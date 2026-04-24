import os
import subprocess
import signal
from pathlib import Path

_proc: subprocess.Popen | None = None
_current_file: str | None = None

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

def guess_media_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    return "video"

def play(filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file

    stop()

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

def stop() -> None:
    global _proc, _current_file

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

def status() -> dict:
    if _proc is None:
        return {"status": "stopped", "filename": None}

    poll = _proc.poll()
    if poll is not None:
        return {"status": "stopped", "filename": None}

    return {"status": "playing", "filename": _current_file}