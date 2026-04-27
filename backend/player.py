import json
import os
import re
import socket
import select
import subprocess
import threading
import time
import sys
from pathlib import Path
from collections import deque

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None
_showing_black: bool = False
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

def guess_media_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    return "video"

def _wait_for_socket(path: str = IPC_SOCKET, timeout: float = 2.0) -> bool:
    """Wait for the IPC socket to become available."""
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

def _capture_startup_logs(proc: subprocess.Popen, max_chars: int = 5000):
    """Capture initial mpv stderr output for debugging."""
    global STARTUP_LOGS
    try:
        start = time.time()
        logs = b""
        while time.time() - start < 3.0:
            ready, _, _ = select.select([proc.stderr], [], [], 0.5)
            if ready:
                chunk = proc.stderr.read1(4096)
                if chunk:
                    logs += chunk
                else:
                    break
            else:
                if proc.poll() is not None:
                    break
            if len(logs) > max_chars:
                break
        
        STARTUP_LOGS = logs.decode('utf-8', errors='ignore')[-max_chars:]
    except Exception as e:
        STARTUP_LOGS = f"Error capturing logs: {e}"

def _send_command(command: list) -> bool:
    """Send a JSON command to mpv via IPC socket, don't wait for response."""
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

def _query_mpv(command: list) -> any:
    """Send a JSON command to mpv via IPC socket and return the response."""
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
    except Exception as e:
        return None

def _query_property(prop: str) -> any:
    """Helper to query a single property."""
    return _query_mpv(["get_property", prop])

def _ensure_mpv_started(display: str | None = None) -> None:
    """Ensure mpv is running in idle mode. If not started, spawn it."""
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
        f"--input-ipc-server={IPC_SOCKET}",
        "--vo=gpu",
        "--gpu-context=drm",
        "--gpu-api=opengl",
        "--opengl-es=yes",
        "--gpu-dumb-mode=yes",
        "--hwdec=drm-copy",
        "--cache=yes",
        "--fit-to-window=yes",
        "--keepaspect=yes",
    ]

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    global STARTUP_LOGS
    STARTUP_LOGS = ""
    _proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _wait_for_socket(IPC_SOCKET, timeout=2.0)

def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file, _current_cue_id, _showing_black

    _showing_black = False
    _ensure_mpv_started(display)
    _current_file = filepath
    _current_cue_id = cue_id

    if media_type is None:
        media_type = guess_media_type(filepath)

    if media_type == "image":
        _send_command(["set", "image-display-duration", "inf"])
    else:
        _send_command(["set", "image-display-duration", "0"])

    _send_command(["loadfile", filepath, "replace"])

    _send_command(["set", "fullscreen", "yes"])

    global STARTUP_LOGS
    STARTUP_LOGS = ""

    with STATS_LOCK:
        _CURRENT_STATS["filename"] = filepath

import pathlib

def stop() -> None:
    global _current_file, _current_cue_id, _showing_black

    _showing_black = True
    black_path = pathlib.Path(__file__).parent / "black.png"
    
    if not black_path.exists():
        print(f"ERROR: black.png not found at {black_path}")
        return
    
    _current_file = "black.png"
    _current_cue_id = None

    _send_command(["set", "image-display-duration", "inf"])
    _send_command(["loadfile", str(black_path), "replace"])
    _send_command(["set", "fullscreen", "yes"])

    with STATS_LOCK:
        _CURRENT_STATS.update({
            "playback-time": None,
            "duration": None,
            "percent-pos": None,
            "fps": None,
            "dropped-frames": None,
            "delayed-frames": None,
        })

def status() -> dict:
    global _showing_black

    if _proc is None:
        return {"status": "idle", "filename": None, "cueId": None}

    poll = _proc.poll()
    if poll is not None:
        return {"status": "idle", "filename": None, "cueId": None}

    if _showing_black:
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
    except:
        pass
    
    test_props = {}
    prop_names = ["time-pos", "duration", "estimated-vf-fps", "drop-frame-count", 
                 "vo-delayed-frame-count", "decoder", "hwdec", "video-codec", "dwidth", "dheight"]
    for p in prop_names:
        try:
            test_props[p] = _query_property(p)
        except:
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
    global _showing_black

    if _proc is None:
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

    poll = _proc.poll()
    if poll is not None:
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

    if _showing_black:
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

    is_idle = _query_property("idle-active")
    if is_idle:
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
        if not _CURRENT_STATS.get("resolution"):
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