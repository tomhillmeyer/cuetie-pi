import os
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import player
import cues

load_dotenv()

media_dir = os.getenv("MEDIA_DIR", "./media")
cues_file = os.getenv("CUES_FILE", "./cues.json")
display = os.getenv("DISPLAY", ":0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(media_dir).mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(lifespan=lifespan)

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

    cue = cues.add_cue(cues_file, safe_name, media_dir)
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