import os
import subprocess
import threading
import time
import sys
from pathlib import Path
from collections import deque

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None
_stderr_output = ""
_stderr_lock = threading.Lock()

_stats_lock = threading.Lock()
_current_stats = {
    "playback-time": None,
    "duration": None,
    "fps": None,
    "paused": False,
    "vsync": None,
}

STATS_BUFFER_SIZE = 100
_stats_history = deque(maxlen=STATS_BUFFER_SIZE)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

def guess_media_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    return "video"

def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file, _current_cue_id

    old_proc = _proc

    if media_type is None:
        media_type = guess_media_type(filepath)

    # Minimal command - basic playback only, no extra flags
    cmd = [
        "mpv",
        "--fullscreen",
        filepath
    ]

    if media_type == "image":
        cmd.append("--image-display-duration=inf")

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    # Simple Popen - no pipes at all
    _proc = subprocess.Popen(cmd, env=env)
    _current_file = filepath
    _current_cue_id = cue_id
    
    # Clear previous stderr tracking
    global _stderr_output
    _stderr_output = ""
    
    # Kill old process after new one starts
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
    
    with _stats_lock:
        _current_stats = {
            "playback-time": None,
            "duration": None,
            "fps": None,
            "paused": False,
            "vsync": None,
        }

def status() -> dict:
    if _proc is None:
        return {"status": "stopped", "filename": None, "cueId": None}

    poll = _proc.poll()
    if poll is not None:
        return {"status": "stopped", "filename": None, "cueId": None}

    return {"status": "playing", "filename": _current_file, "cueId": _current_cue_id}

def debug() -> dict:
    return {
        "proc_running": _proc is not None,
        "proc_poll": _proc.poll() if _proc else None,
        "current_file": _current_file,
        "current_cue_id": _current_cue_id,
        "current_stats": dict(_current_stats),
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
            "vsync": None,
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
            "vsync": None,
        }

    return {
        "status": "playing",
        "paused": False,
        "playback-time": None,
        "duration": None,
        "percent-pos": None,
        "fps": None,
        "video-params": {},
        "audio-params": {},
        "filename": _current_file,
        "media-title": None,
        "video-codec": None,
        "audio-codec": None,
        "vsync": None,
    }