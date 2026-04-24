import json
import os
import subprocess
import threading
import time
from pathlib import Path
from collections import deque
from datetime import datetime

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None

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

def _parse_mpv_line(line: str) -> tuple[str, any] | None:
    """Parse a single line from mpv slave output."""
    line = line.strip()
    if not line:
        return None
    
    if line.startswith("ANS_"):
        parts = line.split("=", 1)
        if len(parts) == 2:
            key = parts[0][4:]
            val = parts[1]
            try:
                if "." in val:
                    return key, float(val)
                else:
                    return key, int(val)
            except ValueError:
                return key, val
    
    if line.startswith("VSYNC:"):
        parts = line.split()
        for part in parts:
            if part.startswith("fps="):
                try:
                    return "vsync", float(part[4:])
                except:
                    pass
    
    if line.startswith("PLAYBACK_TIME="):
        parts = line.split("=", 1)
        if len(parts) == 2:
            try:
                return "playback-time", float(parts[1])
            except:
                pass
    
    if line.startswith("Duration:"):
        parts = line.split()
        for part in parts:
            if part.startswith("total:"):
                try:
                    return "duration", float(part[6:])
                except:
                    pass
    
    return None

def _read_mpv_stdout(proc: subprocess.Popen):
    """Background thread to read and parse mpv stdout."""
    global _current_stats, _stats_history
    
    try:
        for line_bytes in iter(proc.stdout.readline, b""):
            if not line_bytes:
                break
            
            try:
                line = line_bytes.decode("utf-8", errors="ignore")
            except:
                continue
            
            parsed = _parse_mpv_line(line)
            if parsed:
                key, val = parsed
                with _stats_lock:
                    _current_stats[key] = val
                    _stats_history.append({
                        "time": time.time(),
                        key: val
                    })
    
    except Exception:
        pass
    finally:
        with _stats_lock:
            _current_stats = {
                "playback-time": None,
                "duration": None,
                "fps": None,
                "paused": False,
                "vsync": None,
            }

def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file, _current_cue_id

    old_proc = _proc

    if media_type is None:
        media_type = guess_media_type(filepath)

    cmd = [
        "mpv",
        "--fullscreen",
        "--no-terminal",
        "--slave",
        filepath
    ]

    if media_type == "image":
        cmd.append("--image-display-duration=inf")

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    _proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE
    )
    _current_file = filepath
    _current_cue_id = cue_id

    stdout_thread = threading.Thread(target=_read_mpv_stdout, args=(_proc,))
    stdout_thread.daemon = True
    stdout_thread.start()

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

    with _stats_lock:
        playback_time = _current_stats.get("playback-time")
        duration = _current_stats.get("duration")
        fps = _current_stats.get("fps")
        paused = _current_stats.get("paused", False)
        vsync = _current_stats.get("vsync")
    
    percent_pos = None
    if playback_time and duration and duration > 0:
        percent_pos = (playback_time / duration) * 100

    return {
        "status": "playing",
        "paused": paused,
        "playback-time": playback_time,
        "duration": duration,
        "percent-pos": percent_pos,
        "fps": fps,
        "video-params": {},
        "audio-params": {},
        "filename": _current_file,
        "media-title": None,
        "video-codec": None,
        "audio-codec": None,
        "vsync": vsync,
    }