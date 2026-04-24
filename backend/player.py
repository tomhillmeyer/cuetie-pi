import os
import re
import subprocess
import threading
import time
import sys
from pathlib import Path
from collections import deque
from datetime import datetime

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None

LOG_FILE = "/tmp/mpv.log"

_stats_lock = threading.Lock()
_current_stats = {
    "playback-time": None,
    "duration": None,
    "duration-seconds": None,
    "percent-pos": None,
    "fps-source": None,
    "resolution": None,
    "pixfmt": None,
    "video-codec": None,
    "audio-codec": None,
    "audio-samplerate": None,
    "dropped-frames": None,
    "media-title": None,
    "vo": None,
    "ao": None,
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

def _parse_log_line(line: str) -> dict | None:
    """Parse a single line from mpv log output."""
    result = {}
    line = line.strip()
    
    # Position: AV: 00:00:00 / 00:02:39 (0%) A-V: 0.000 Dropped: 12
    # or: AV: 00:00:00 / 00:02:39 (0%) A-V: 0.000
    pos_match = re.search(r'AV:\s+(\d+:\d+:\d+)\s+/\s+(\d+:\d+:\d+)\s+\((\d+)%\)', line)
    if pos_match:
        current_time = pos_match.group(1)
        duration = pos_match.group(2)
        percent = int(pos_match.group(3))
        
        # Convert to seconds
        parts = current_time.split(':')
        current_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        parts = duration.split(':')
        duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        result['playback-time'] = current_seconds
        result['duration-seconds'] = duration_seconds
        result['percent-pos'] = percent
    
    # Dropped frames: Dropped: 12
    dropped_match = re.search(r'Dropped:\s+(\d+)', line)
    if dropped_match:
        result['dropped-frames'] = int(dropped_match.group(1))
    
    return result if result else None

def _read_mpv_log():
    """Background thread to read and parse mpv log file."""
    global _current_stats, _stats_history
    
    last_size = 0
    
    try:
        while True:
            if _proc is None:
                break
            
            try:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, 'r') as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                        last_size = f.tell()
                        
                        for line in new_lines:
                            parsed = _parse_log_line(line)
                            if parsed:
                                with _stats_lock:
                                    _current_stats.update(parsed)
                                    _stats_history.append({
                                        "time": time.time(),
                                        "stats": dict(_current_stats)
                                    })
                
                time.sleep(0.1)
            except Exception:
                pass
    
    except Exception:
        pass

def _extract_static_info(lines: list[str]) -> dict:
    """Extract static info from initial log lines."""
    info = {}
    
    for line in lines:
        # Video info: ● Video --vid=1 --vlang=eng (h264 1080x1920 60 fps) [default]
        # Or: ● Image --vid=1 (png 1080x1920)
        video_match = re.search(r'●\s+(Video|Image)\s+.*?\s+\((\w+)\s+(\d+)x(\d+)\s+(\d+)\s*fps)\)', line)
        if video_match:
            info['video-codec'] = video_match.group(2)
            info['fps-source'] = int(video_match.group(5))
            info['resolution'] = f"{video_match.group(3)}x{video_match.group(4)}"
            
        # VO: [gpu] 1080x1920 yuv420p
        vo_match = re.search(r'VO:\s+\[(\w+)\]\s+(\d+)x(\d+)\s+(\w+)', line)
        if vo_match:
            info['vo'] = vo_match.group(1)
            if not info.get('resolution'):
                info['resolution'] = f"{vo_match.group(2)}x{vo_match.group(3)}"
            info['pixfmt'] = vo_match.group(4)
        
        # AO: [alsa] 48000Hz stereo 2ch float
        ao_match = re.search(r'AO:\s+\[(\w+)\]\s+(\d+)Hz\s+(\w+)\s+(\d+)ch', line)
        if ao_match:
            info['ao'] = ao_match.group(1)
            info['audio-samplerate'] = int(ao_match.group(2))
            info['audio-codec'] = f"{ao_match.group(3)} {ao_match.group(4)}ch"
    
    return info

def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file, _current_cue_id

    old_proc = _proc

    if media_type is None:
        media_type = guess_media_type(filepath)

    # Build command with log-file (use = syntax)
    cmd = [
        "mpv",
        "--fullscreen",
        f"--log-file={LOG_FILE}",
        filepath
    ]

    if media_type == "image":
        cmd.append("--image-display-duration=inf")

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    # Clear log file before starting
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    # Start mpv
    _proc = subprocess.Popen(cmd, env=env)
    _current_file = filepath
    _current_cue_id = cue_id
    
    # Start log reader thread
    log_thread = threading.Thread(target=_read_mpv_log)
    log_thread.daemon = True
    log_thread.start()
    
    # Extract static info from initial lines
    time.sleep(0.3)
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            static_info = _extract_static_info(lines)
            with _stats_lock:
                _current_stats.update(static_info)
    
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
            "duration-seconds": None,
            "percent-pos": None,
            "fps-source": None,
            "resolution": None,
            "pixfmt": None,
            "video-codec": None,
            "audio-codec": None,
            "audio-samplerate": None,
            "dropped-frames": None,
            "media-title": None,
            "vo": None,
            "ao": None,
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
            "status": "stopped",
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

    with _stats_lock:
        playback_time = _current_stats.get("playback-time")
        duration_seconds = _current_stats.get("duration-seconds")
        percent_pos = _current_stats.get("percent-pos")
        fps = _current_stats.get("fps-source")
        resolution = _current_stats.get("resolution")
        pixfmt = _current_stats.get("pixfmt")
        video_codec = _current_stats.get("video-codec")
        audio_codec = _current_stats.get("audio-codec")
        audio_samplerate = _current_stats.get("audio-samplerate")
        dropped = _current_stats.get("dropped-frames")
        vo = _current_stats.get("vo")
        ao = _current_stats.get("ao")
        media_title = _current_stats.get("media-title")
    
    return {
        "status": "playing",
        "paused": False,
        "playback-time": playback_time,
        "duration": duration_seconds,
        "percent-pos": percent_pos,
        "fps": fps,
        "vsync": None,
        "video-params": {
            "w": resolution.split('x')[0] if resolution else None,
            "h": resolution.split('x')[1] if resolution else None,
            "pixelformat": pixfmt,
        } if resolution else {},
        "audio-params": {
            "samplerate": audio_samplerate,
        } if audio_samplerate else {},
        "filename": _current_file,
        "media-title": media_title,
        "video-codec": video_codec,
        "audio-codec": audio_codec,
        "dropped-frames": dropped,
    }