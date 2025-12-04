import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROFILES_DIR = Path(__file__).resolve().parents[1] / "profiles"


def ensure_profile_dir(target: str) -> Path:
    p = PROFILES_DIR / target
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_metadata(target: str) -> Dict[str, Any]:
    p = ensure_profile_dir(target) / "metadata.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_metadata(target: str, metadata: Dict[str, Any]) -> None:
    p = ensure_profile_dir(target) / "metadata.json"
    metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"
    _write_json(p, metadata)


def add_module_usage(target: str, module_name: str) -> None:
    meta = load_metadata(target)
    mods = meta.get("modules", [])
    if module_name not in mods:
        mods.append(module_name)
    meta["modules"] = mods
    if "first_seen" not in meta:
        meta["first_seen"] = datetime.utcnow().isoformat() + "Z"
    save_metadata(target, meta)


def update_collection(target: str, kind: str, items: List[Any]) -> None:
    """kind: domains|ips|emails|social"""
    d = ensure_profile_dir(target)
    path = d / f"{kind}.json"
    existing: List[Any] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    # naive merge dedupe
    merged = existing[:]
    for it in items:
        if it not in merged:
            merged.append(it)

    _write_json(path, merged)
    # update metadata modules/time
    add_module_usage(target, f"update_{kind}")


def add_note(target: str, note: str, author: Optional[str] = None) -> None:
    d = ensure_profile_dir(target)
    notes_path = d / "notes.md"
    ts = datetime.utcnow().isoformat() + "Z"
    header = f"- [{ts}]"
    if author:
        header += f" ({author})"
    header += "\n"
    # If notes file doesn't exist, start with empty content
    existing = ""
    if notes_path.exists():
        try:
            existing = notes_path.read_text(encoding="utf-8")
        except Exception:
            existing = ""
    notes_path.write_text(existing + header + note + "\n\n", encoding="utf-8")
    add_module_usage(target, "note")


def get_profile_dir(target: str) -> Path:
    return ensure_profile_dir(target)
"""Profile management for scan presets.

Profiles may live in `config/profiles.yml` or `profiles.yaml` at repo root.
This loader provides a safe fallback and a listing function for the CLI.
"""
from pathlib import Path
from typing import Dict
import yaml


def _profiles_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    return [repo_root / "config" / "profiles.yml", repo_root / "profiles.yaml"]


def load_profiles() -> Dict[str, dict]:
    """Load and return profiles mapping. Empty dict if none found or parse error."""
    for p in _profiles_paths():
        if p.exists():
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    return data
            except Exception:
                return {}
    return {}


def list_profiles() -> list[str]:
    return sorted(list(load_profiles().keys()))
