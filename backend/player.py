import json
import os
import re
import socket
import subprocess
import threading
import time
import sys
from pathlib import Path
from collections import deque

_proc: subprocess.Popen | None = None
_current_file: str | None = None
_current_cue_id: str | None = None
IPC_SOCKET = "/tmp/mpv-socket"

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

def play(cue_id: str, filepath: str, media_type: str | None = None, display: str | None = None) -> None:
    global _proc, _current_file, _current_cue_id

    old_proc = _proc

    if media_type is None:
        media_type = guess_media_type(filepath)

    # Clean up old socket if it exists
    if os.path.exists(IPC_SOCKET):
        try:
            os.remove(IPC_SOCKET)
        except Exception:
            pass

    # Build command with hardware acceleration for Pi 4
    cmd = [
        "mpv",
        "--fullscreen",
        f"--input-ipc-server={IPC_SOCKET}",
        "--hwdec=vaapi",
        "--vo=gpu",
        "--video-sync=display-resample",
        "--cache=yes",
        filepath
    ]

    if media_type == "image":
        cmd.append("--image-display-duration=inf")

    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    # Start mpv
    _proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _current_file = filepath
    _current_cue_id = cue_id
    
    # Wait for socket to become available
    _wait_for_socket(IPC_SOCKET, timeout=1.0)
    
    # Initialize stats
    with STATS_LOCK:
        _CURRENT_STATS["filename"] = filepath
    
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
    
    # Clean up socket
    if os.path.exists(IPC_SOCKET):
        try:
            os.remove(IPC_SOCKET)
        except Exception:
            pass
    
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
    if _proc is None:
        return {"status": "stopped", "filename": None, "cueId": None}

    poll = _proc.poll()
    if poll is not None:
        return {"status": "stopped", "filename": None, "cueId": None}

    return {"status": "playing", "filename": _current_file, "cueId": _current_cue_id}

def debug() -> dict:
    socket_exists = os.path.exists(IPC_SOCKET)
    
    # Try to get available properties
    available_props = []
    try:
        available_props = _query_mpv(["get_property_list"])
    except:
        pass
    
    # Query a few key properties to see values
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
        "available_properties": available_props[:50] if available_props else [],  # Limit to 50
        "test_properties": test_props,
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

    # Query mpv for stats via IPC socket
    stats = {}
    
    # Position and duration
    time_pos = _query_property("time-pos")
    duration = _query_property("duration")
    percent_pos = _query_property("percent-pos")
    
    # FPS and frame counts - try multiple property names
    fps = _query_property("estimated-vf-fps")
    
    # Try different property names for dropped frames
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
    
    # Query hardware decode status
    hwdec = _query_property("hwdec")
    decoder = _query_property("decoder")
    
    # Metadata (only query once at start)
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