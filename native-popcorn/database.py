import json
import os
from pathlib import Path

# Config directory mapping
CONFIG_DIR = Path.home() / ".config" / "native-popcorn"
DB_FILE = CONFIG_DIR / "data.json"

def _ensure_db():
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
    if not DB_FILE.exists():
        with open(DB_FILE, "w") as f:
            json.dump({"favorites": [], "watched": []}, f)

def _read_db():
    _ensure_db()
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"favorites": [], "watched": []}

def _write_db(data):
    _ensure_db()
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- Favorites ---

def get_favorites():
    return _read_db().get("favorites", [])

def add_favorite(item):
    db = _read_db()
    if not any(f.get("id") == item.get("id") for f in db.get("favorites", [])):
        db.setdefault("favorites", []).insert(0, item)
        _write_db(db)

def remove_favorite(item_id):
    db = _read_db()
    db["favorites"] = [f for f in db.get("favorites", []) if f.get("id") != item_id]
    _write_db(db)

def is_favorite(item_id):
    return any(f.get("id") == item_id for f in _read_db().get("favorites", []))

# --- Watched ---

def get_watched():
    return _read_db().get("watched", [])

def add_watched(item):
    db = _read_db()
    if not any(f.get("id") == item.get("id") for f in db.get("watched", [])):
        db.setdefault("watched", []).insert(0, item)
        _write_db(db)

def remove_watched(item_id):
    db = _read_db()
    db["watched"] = [f for f in db.get("watched", []) if f.get("id") != item_id]
    _write_db(db)

def is_watched(item_id):
    return any(f.get("id") == item_id for f in _read_db().get("watched", []))
