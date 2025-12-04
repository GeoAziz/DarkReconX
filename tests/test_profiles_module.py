import json
from pathlib import Path

import pytest

import core.profiles as profiles


def test_profiles_save_load_and_notes(tmp_path, monkeypatch):
    # Redirect profiles directory to tmp_path
    monkeypatch.setattr(profiles, "PROFILES_DIR", tmp_path)

    target = "example.com"
    # Ensure metadata is empty initially
    meta = profiles.load_metadata(target)
    assert isinstance(meta, dict)

    # Add module usage and save metadata
    profiles.add_module_usage(target, "whois")
    m2 = profiles.load_metadata(target)
    assert "modules" in m2 and "whois" in m2["modules"]

    # Update collections
    profiles.update_collection(target, "domains", ["a.example.com", "b.example.com"])
    p = tmp_path / target / "domains.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "a.example.com" in data

    # Add a note and verify file exists and contains the note
    profiles.add_note(target, "Investigate ASN")
    notes = tmp_path / target / "notes.md"
    assert notes.exists()
    content = notes.read_text(encoding="utf-8")
    assert "Investigate ASN" in content

