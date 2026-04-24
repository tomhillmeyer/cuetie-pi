import json
import os
import socket
import subprocess
import signal
import time
from pathlib import Path

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None

IPC_SOCKET = "/tmp/mpv.sock"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

def guess_media_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    return "video"

def _mpv_command(property_name: str):
    """Send a command to MPV via IPC socket and return the result."""
    if _proc is None:
        return None
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        sock.connect(IPC_SOCKET)
        
        request = json.dumps({"command": ["get_property", property_name], "request_id": 1})
        sock.send(request.encode() + b"\n")
        
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break
        
        sock.close()
        
        if response:
            data = json.loads(response.decode())
            if "error" in data and data["error"] == "success":
                return data.get("data")
        return None
    except Exception:
        return None

def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file, _current_cue_id

    old_proc = _proc

    if media_type is None:
        media_type = guess_media_type(filepath)

    cmd = [
        "mpv",
        "--fullscreen",
        "--no-terminal",
        filepath
    ]

    if media_type == "image":
        cmd.append("--image-display-duration=inf")

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    _proc = subprocess.Popen(cmd, env=env)
    _current_file = filepath
    _current_cue_id = cue_id

    if old_proc is not None:
        time.sleep(0.1)
        try:
            old_proc.kill()
            old_proc.wait()
        except Exception:
            pass

def stop() -> None:
    global _proc, _current_file, _current_cue_id

    if _proc is not None:
        try:
            _proc.terminate()
            _proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _proc.kill()
            _proc.wait()
        except Exception:
            pass
        _proc = None
        _current_file = None
        _current_cue_id = None

def status() -> dict:
    if _proc is None:
        return {"status": "stopped", "filename": None, "cueId": None}

    poll = _proc.poll()
    if poll is not None:
        return {"status": "stopped", "filename": None, "cueId": None}

    return {"status": "playing", "filename": _current_file, "cueId": _current_cue_id}

def debug() -> dict:
    socket_exists = os.path.exists(IPC_SOCKET) if IPC_SOCKET else False
    
    return {
        "proc_running": _proc is not None,
        "proc_poll": _proc.poll() if _proc else None,
        "socket_exists": socket_exists,
        "socket_path": IPC_SOCKET,
        "current_file": _current_file,
        "current_cue_id": _current_cue_id,
    }

def get_stats() -> dict:
    if _proc is None:
        return {
            "status": "stopped",
            "paused": False,
            "playback-time": None,
            "duration": None,
            "percent-pos": None,
            "fps": None,
            "video-params": {},
            "audio-params": {},
            "filename": None,
            "media-title": None,
            "video-codec": None,
            "audio-codec": None,
        }

    poll = _proc.poll()
    if poll is not None:
        return {
            "status": "stopped",
            "paused": False,
            "playback-time": None,
            "duration": None,
            "percent-pos": None,
            "fps": None,
            "video-params": {},
            "audio-params": {},
            "filename": None,
            "media-title": None,
            "video-codec": None,
            "audio-codec": None,
        }

    properties = [
        "pause",
        "playback-time",
        "duration",
        "percent-pos",
        "fps",
        "video-params",
        "audio-params",
        "filename",
        "media-title",
        "video-codec",
        "audio-codec",
    ]

    stats = {}
    for prop in properties:
        stats[prop] = _mpv_command(prop)

    return {
        "status": "playing",
        "paused": stats.get("pause", False),
        "playback-time": stats.get("playback-time"),
        "duration": stats.get("duration"),
        "percent-pos": stats.get("percent-pos"),
        "fps": stats.get("fps"),
        "video-params": stats.get("video-params", {}),
        "audio-params": stats.get("audio-params", {}),
        "filename": stats.get("filename"),
        "media-title": stats.get("media-title"),
        "video-codec": stats.get("video-codec"),
        "audio-codec": stats.get("audio-codec"),
    }