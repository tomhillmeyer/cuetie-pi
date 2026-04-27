import os
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from dotenv import load_dotenv

import player
import cues
import keyboard

load_dotenv()

media_dir = os.getenv("MEDIA_DIR", "./media")
cues_file = os.getenv("CUES_FILE", "./cues.json")
display = os.getenv("DISPLAY", ":0")

class AppState:
    def __init__(self):
        self.current_index: int = 0
        self.num_cues: int = 0

state = AppState()

def update_num_cues():
    all_cues = cues.load_cues(cues_file)
    state.num_cues = len(all_cues)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(media_dir).mkdir(parents=True, exist_ok=True)
    update_num_cues()
    try:
        keyboard.start_keyboard_listener()
    except Exception as e:
        print(f"Keyboard listener failed to start: {e}")
    yield

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def add_cross_origin_isolation(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response

@app.get("/api/cues")
def get_cues():
    return cues.load_cues(cues_file)

@app.post("/api/upload")
async def upload_media(file: UploadFile = File(...)):
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_name = Path(filename).name
    save_path = Path(media_dir) / safe_name
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    media_type = cues.guess_media_type(safe_name)
    cue = cues.add_cue(cues_file, safe_name, media_dir, "ready")

    return cue

@app.post("/api/cues/reorder")
def reorder_cues(body: dict):
    cue_ids = body.get("cueIds", [])
    reordered = cues.reorder_cues(cues_file, cue_ids)
    return reordered

@app.delete("/api/cues/{cue_id}")
def delete_cue(cue_id: str):
    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")

    file_path = Path(cue["path"])
    if file_path.exists():
        file_path.unlink()

    cues.remove_cue(cues_file, cue_id)
    return {"success": True}

@app.post("/api/cues/{cue_id}/play")
def play_cue(cue_id: str):
    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")

    file_path = Path(cue["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    player.play(cue_id, str(file_path), cue.get("type"), display)
    return {"success": True, "cue": cue}

@app.post("/api/stop")
def stop_playback():
    player.stop()
    return {"success": True}

@app.get("/api/status")
def get_status():
    return player.status()

@app.get("/api/stats")
def get_stats():
    return player.get_stats()

@app.get("/api/debug")
def get_debug():
    return player.debug()

@app.post("/api/go")
def go_next():
    """Advance to and play the next cue. Wraps to cue 1 if at end."""
    update_num_cues()
    if state.num_cues == 0:
        return {"success": False, "error": "No cues in list"}
    
    if state.current_index >= state.num_cues:
        state.current_index = 1
    else:
        state.current_index += 1
    
    cue = cues.play_by_index(cues_file, state.current_index, display)
    return {"success": True, "cue": cue, "index": state.current_index}

@app.post("/api/go/{n}")
def go_to(n: int):
    """Play cue number n (1-based index)."""
    update_num_cues()
    if state.num_cues == 0:
        return {"success": False, "error": "No cues in list"}
    
    if n < 1 or n > state.num_cues:
        return {"success": False, "error": f"Invalid cue number: {n}"}
    
    state.current_index = n
    cue = cues.play_by_index(cues_file, n, display)
    return {"success": True, "cue": cue, "index": n}

@app.post("/api/previous")
def go_previous():
    """Play the previous cue. Stays at cue 1 if already at cue 1."""
    update_num_cues()
    if state.num_cues == 0:
        return {"success": False, "error": "No cues in list"}
    
    if state.current_index <= 1:
        state.current_index = 1
    else:
        state.current_index -= 1
    
    cue = cues.play_by_index(cues_file, state.current_index, display)
    return {"success": True, "cue": cue, "index": state.current_index}

@app.get("/api/current")
def get_current():
    """Return the current cue number and metadata."""
    update_num_cues()
    if state.num_cues == 0:
        return {"index": 0, "cue": None}
    
    if state.current_index == 0:
        return {"index": 0, "cue": None}
    
    all_cues = cues.load_cues(cues_file)
    cue = all_cues[state.current_index - 1] if state.current_index <= len(all_cues) else None
    return {"index": state.current_index, "cue": cue}

@app.post("/api/reset")
def reset_pointer():
    """Reset cue pointer to 0 without playing."""
    state.current_index = 0
    return {"success": True, "index": 0}

app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")