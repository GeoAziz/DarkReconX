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
