import json
from pathlib import Path

_FILE = Path(__file__).parent / "config.json"
_DEFAULTS = {
    "ROBLOX_API_KEY":   "",
    "ROBLOX_USER_ID":   "",
    "DOWNLOADS_FOLDER": "downloads",
    "UPLOAD_JSON":      "upload.json",
    "SPEED":            2.3,
    "AMPLIFY_DB":       -4,
}

def load() -> dict:
    if _FILE.exists():
        try:
            return {**_DEFAULTS, **json.loads(_FILE.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return dict(_DEFAULTS)

def save(data: dict):
    _FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

_cfg = load()

ROBLOX_API_KEY   = _cfg["ROBLOX_API_KEY"]
ROBLOX_USER_ID   = _cfg["ROBLOX_USER_ID"]
DOWNLOADS_FOLDER = _cfg["DOWNLOADS_FOLDER"]
UPLOAD_JSON      = _cfg["UPLOAD_JSON"]
SPEED            = _cfg["SPEED"]
AMPLIFY_DB       = _cfg["AMPLIFY_DB"]
