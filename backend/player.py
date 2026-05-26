import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

from PIL import Image

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None
_showing_black: bool = False
_showing_splash: bool = False
IPC_SOCKET = "/tmp/mpv-socket"

STARTUP_LOGS = ""

STATS_LOCK = threading.Lock()
_CURRENT_STATS = {
    "playback-time": None,
    "duration": None,
    "percent-pos": None,
    "fps": None,
    "dropped-frames": None,
    "delayed-frames": None,
    "resolution": None,
    "video-codec": None,
    "audio-codec": None,
    "audio-samplerate": None,
    "filename": None,
    "media-title": None,
    "vo": None,
    "ao": None,
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}


def resize_image(filepath: str, max_dim: int = 4096) -> None:
    ext = Path(filepath).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        return
    img = Image.open(filepath)
    if max(img.width, img.height) <= max_dim:
        return
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    if ext in (".jpg", ".jpeg"):
        img = img.convert("RGB")
        img.save(filepath, "JPEG", quality=85)
    else:
        img.save(filepath)


def guess_media_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    return "video"


def _wait_for_socket(path: str = IPC_SOCKET, timeout: float = 3.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(0.1)
            s.connect(path)
            s.close()
            return True
        except Exception:
            time.sleep(0.05)
    return False


def _send_command(command: list) -> bool:
    if _proc is None:
        return False

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(IPC_SOCKET)

        request = json.dumps({"command": command, "request_id": 1}) + "\n"
        s.sendall(request.encode())
        s.close()
        return True
    except Exception:
        return False


def _query_mpv(command: list):
    if _proc is None:
        return None

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(IPC_SOCKET)

        request = json.dumps({"command": command, "request_id": 1}) + "\n"
        s.sendall(request.encode())

        response = b""
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\n" in response:
                    break
            except socket.timeout:
                break

        s.close()

        if response:
            data = json.loads(response.decode())
            if "error" in data and data["error"] == "success":
                return data.get("data")
        return None
    except Exception:
        return None


def _query_property(prop: str):
    return _query_mpv(["get_property", prop])


def _send_commands_sequential(commands: list[list], timeout: float = 5.0) -> bool:
    if _proc is None:
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(IPC_SOCKET)

        for i, cmd in enumerate(commands):
            msg = json.dumps({"command": cmd, "request_id": i}) + "\n"
            s.sendall(msg.encode())

            buf = b""
            deadline = time.time() + 2.0
            got_ack = False
            while time.time() < deadline and not got_ack:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                            if obj.get("request_id") == i:
                                got_ack = True
                                break
                        except json.JSONDecodeError:
                            pass
                except socket.timeout:
                    break

        s.close()
        return True
    except Exception:
        return False


def _ensure_mpv_started(display: str | None = None) -> None:
    global _proc

    if _proc is not None and _proc.poll() is None:
        return

    if os.path.exists(IPC_SOCKET):
        try:
            os.remove(IPC_SOCKET)
        except Exception:
            pass

    cmd = [
        "mpv",
        "--idle=yes",
        "--force-window=no",
        "--keep-open=yes",
        "--osd-level=0",
        "--gpu-dumb-mode=yes",
        f"--input-ipc-server={IPC_SOCKET}",
        "--vo=gpu",
        "--gpu-context=wayland",
        "--gpu-api=opengl",
        "--opengl-es=yes",
        "--hwdec=drm-copy",
        "--cache=yes",
    ]

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    _proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _wait_for_socket(IPC_SOCKET, timeout=5.0)


def _load_via_mpv(filepath: str, media_type: str | None = None, display: str | None = None, loop: bool = False) -> bool:
    for attempt in range(3):
        _ensure_mpv_started(display)
        cmds = [
            ["set", "image-display-duration", "inf" if media_type == "image" else "0"],
            ["loadfile", filepath, "replace"],
            ["set", "fullscreen", "yes"],
            ["set", "pause", "no"],
        ]
        if media_type == "video":
            cmds.append(["set", "loop-file", "inf" if loop else "no"])
        if _send_commands_sequential(cmds):
            return True
        print(f"[player] mpv loadfile attempt {attempt + 1} failed, retrying...")
        time.sleep(0.5)
    print(f"[player] mpv load failed after 3 attempts")
    return False


def show_splash(display: str | None = None) -> None:
    global _current_file, _current_cue_id, _showing_black, _showing_splash

    import generate_splash

    splash_path = Path(__file__).parent / "splash.png"
    logo_path = Path(__file__).parent.parent / "frontend" / "dist" / "logo.png"

    generate_splash.generate(str(logo_path), str(splash_path))

    _showing_splash = True
    _showing_black = False
    _current_file = "splash.png"
    _current_cue_id = None

    _ensure_mpv_started(display)
    _send_commands_sequential([
        ["set", "image-display-duration", "inf"],
        ["loadfile", str(splash_path), "replace"],
        ["set", "fullscreen", "yes"],
    ])


def refresh_splash() -> None:
    if not _showing_splash:
        return
    splash_path = Path(__file__).parent / "splash.png"
    _send_commands_sequential([
        ["loadfile", str(splash_path), "replace"],
        ["set", "fullscreen", "yes"],
    ])


def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None, loop: bool = False) -> None:
    global _current_file, _current_cue_id, _showing_black, _showing_splash

    _showing_splash = False
    _showing_black = False
    _current_file = filepath
    _current_cue_id = cue_id

    _load_via_mpv(filepath, media_type, display, loop)

    global STARTUP_LOGS, _CURRENT_STATS
    STARTUP_LOGS = ""

    with STATS_LOCK:
        _CURRENT_STATS["filename"] = filepath


def stop() -> None:
    global _current_file, _current_cue_id, _showing_black

    _showing_black = True
    black_path = Path(__file__).parent / "black.png"

    if black_path.exists():
        _send_commands_sequential([
            ["loadfile", str(black_path), "replace"],
            ["set", "fullscreen", "yes"],
        ])

    _current_file = "black.png"
    _current_cue_id = None

    with STATS_LOCK:
        _CURRENT_STATS.update({
            "playback-time": None,
            "duration": None,
            "percent-pos": None,
            "fps": None,
            "dropped-frames": None,
            "delayed-frames": None,
            "resolution": None,
            "video-codec": None,
        })


def status() -> dict:
    global _showing_black, _showing_splash

    if _showing_black or _showing_splash:
        return {"status": "idle", "filename": None, "cueId": None}

    if _proc is None:
        return {"status": "idle", "filename": None, "cueId": None}

    poll = _proc.poll()
    if poll is not None:
        return {"status": "idle", "filename": None, "cueId": None}

    is_idle = _query_property("idle-active")
    if is_idle:
        return {"status": "idle", "filename": None, "cueId": None}

    return {"status": "playing", "filename": _current_file, "cueId": _current_cue_id}


def debug() -> dict:
    global STARTUP_LOGS
    socket_exists = os.path.exists(IPC_SOCKET)

    logs = STARTUP_LOGS

    available_props = []
    try:
        available_props = _query_mpv(["get_property_list"])
    except Exception:
        pass

    test_props = {}
    prop_names = [
        "time-pos", "duration", "estimated-vf-fps", "drop-frame-count",
        "vo-delayed-frame-count", "decoder", "hwdec", "video-codec",
        "dwidth", "dheight",
    ]
    for p in prop_names:
        try:
            test_props[p] = _query_property(p)
        except Exception:
            test_props[p] = None

    return {
        "proc_running": _proc is not None,
        "proc_poll": _proc.poll() if _proc else None,
        "current_file": _current_file,
        "current_cue_id": _current_cue_id,
        "socket_exists": socket_exists,
        "socket_path": IPC_SOCKET,
        "available_properties": available_props[:50] if available_props else [],
        "test_properties": test_props,
        "startup_logs": logs,
    }


def get_stats() -> dict:
    global _showing_black, _showing_splash

    if _showing_black or _showing_splash:
        return _idle_stats()

    if _proc is None:
        return _idle_stats()

    poll = _proc.poll()
    if poll is not None:
        return _idle_stats()

    is_idle = _query_property("idle-active")
    if is_idle:
        return _idle_stats()

    time_pos = _query_property("time-pos")
    duration = _query_property("duration")
    percent_pos = _query_property("percent-pos")
    fps = _query_property("estimated-vf-fps")

    dropped_frames = None
    for prop in ["drop-frame-count", "frame-drop-count", "vo-drop-frame-count", "dropped"]:
        dropped_frames = _query_property(prop)
        if dropped_frames is not None:
            break

    delayed_frames = None
    for prop in ["vo-delayed-frame-count", "delayed-frame-count", "delayed"]:
        delayed_frames = _query_property(prop)
        if delayed_frames is not None:
            break

    hwdec = _query_property("hwdec")
    decoder = _query_property("decoder")

    with STATS_LOCK:
        video_params = _query_property("video-params")
        if video_params:
            _CURRENT_STATS["resolution"] = f"{video_params.get('w', 0)}x{video_params.get('h', 0)}"
            _CURRENT_STATS["video-codec"] = video_params.get('codec', None)

        audio_params = _query_property("audio-params")
        if audio_params:
            _CURRENT_STATS["audio-samplerate"] = audio_params.get('samplerate', None)
            _CURRENT_STATS["audio-codec"] = audio_params.get('codec', None)

        filename = _query_property("filename")
        if filename:
            _CURRENT_STATS["filename"] = filename

        media_title = _query_property("media-title")
        if media_title:
            _CURRENT_STATS["media-title"] = media_title

        vo = _query_property("vo")
        if vo:
            _CURRENT_STATS["vo"] = vo

        ao = _query_property("ao")
        if ao:
            _CURRENT_STATS["ao"] = ao

    with STATS_LOCK:
        _CURRENT_STATS["playback-time"] = time_pos
        _CURRENT_STATS["duration"] = duration
        _CURRENT_STATS["percent-pos"] = percent_pos
        _CURRENT_STATS["fps"] = fps
        _CURRENT_STATS["dropped-frames"] = dropped_frames
        _CURRENT_STATS["delayed-frames"] = delayed_frames

    resolution = _CURRENT_STATS.get("resolution", "?x?")

    return {
        "status": "playing",
        "paused": False,
        "playback-time": time_pos,
        "duration": duration,
        "percent-pos": percent_pos,
        "fps": fps,
        "vsync": fps,
        "hwdec": hwdec,
        "decoder": decoder,
        "video-params": {
            "w": resolution.split('x')[0] if resolution else None,
            "h": resolution.split('x')[1] if resolution else None,
        },
        "audio-params": {
            "samplerate": _CURRENT_STATS.get("audio-samplerate"),
        },
        "filename": _CURRENT_STATS.get("filename"),
        "media-title": _CURRENT_STATS.get("media-title"),
        "video-codec": _CURRENT_STATS.get("video-codec"),
        "audio-codec": _CURRENT_STATS.get("audio-codec"),
        "dropped-frames": dropped_frames,
    }


def _idle_stats() -> dict:
    return {
        "status": "idle",
        "paused": False,
        "playback-time": None,
        "duration": None,
        "percent-pos": None,
        "fps": None,
        "vsync": None,
        "video-params": {},
        "audio-params": {},
        "filename": None,
        "media-title": None,
        "video-codec": None,
        "audio-codec": None,
        "dropped-frames": None,
    }


def get_current_playing_cue_id() -> str | None:
    global _current_cue_id, _showing_black

    if _showing_black:
        return None

    if _proc is None:
        return None

    poll = _proc.poll()
    if poll is not None:
        return None

    return _current_cue_id
