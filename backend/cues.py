import json
import uuid
from pathlib import Path

Cue = dict

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

def guess_media_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    return "video"

def load_cues(cues_file: str) -> list[Cue]:
    path = Path(cues_file)
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_cues(cues_file: str, cues: list[Cue]) -> None:
    path = Path(cues_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cues, f, indent=2)

def add_cue(cues_file: str, filename: str, media_dir: str, status: str = "ready") -> Cue:
    cue_id = str(uuid.uuid4())
    cue = {
        "id": cue_id,
        "filename": filename,
        "label": filename,
        "type": guess_media_type(filename),
        "path": f"{media_dir}/{filename}",
        "status": status
    }

    cues = load_cues(cues_file)
    cues.append(cue)
    save_cues(cues_file, cues)

    return cue

def update_cue_status(cues_file: str, cue_id: str, status: str, error_message: str = None) -> bool:
    cues = load_cues(cues_file)
    for cue in cues:
        if cue["id"] == cue_id:
            cue["status"] = status
            if error_message:
                cue["error_message"] = error_message
            save_cues(cues_file, cues)
            return True
    return False

def remove_cue(cues_file: str, cue_id: str) -> bool:
    cues = load_cues(cues_file)
    cues = [c for c in cues if c["id"] != cue_id]
    save_cues(cues_file, cues)
    return True

def reorder_cues(cues_file: str, cue_ids: list[str]) -> list[Cue]:
    cues = load_cues(cues_file)
    id_to_cue = {c["id"]: c for c in cues}
    reordered = [id_to_cue[cid] for cid in cue_ids if cid in id_to_cue]
    save_cues(cues_file, reordered)
    return reordered