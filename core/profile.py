"""Simple user profile persistence for storing last known location.

Stores a JSON file `user_profile.json` in the project root (same directory as this module's parent).
Structure:
{
  "last_location": {"village": str, "state": str, "lat": float, "lon": float, "timestamp": float}
}
"""
from __future__ import annotations
import json, time, os, pathlib
from typing import Optional, Dict, Any

_PROFILE_FILENAME = "user_profile.json"
_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PROFILE_PATH = _ROOT / _PROFILE_FILENAME

def load_profile() -> Dict[str, Any]:
    try:
        with open(_PROFILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_profile(data: Dict[str, Any]):
    try:
        with open(_PROFILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def update_last_location(village: str, state: str, lat: float, lon: float):
    data = load_profile()
    data['last_location'] = {
        'village': village,
        'state': state,
        'lat': lat,
        'lon': lon,
        'timestamp': time.time()
    }
    save_profile(data)

def get_last_location() -> Optional[Dict[str, Any]]:
    prof = load_profile()
    loc = prof.get('last_location')
    if not loc:
        return None
    return loc

__all__ = ['load_profile', 'save_profile', 'update_last_location', 'get_last_location']
