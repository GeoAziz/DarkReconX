from pathlib import Path
from typing import Dict
from datetime import datetime

from .profiles import get_profile_dir, load_metadata


def generate_html_report(target: str, profile: Dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = load_metadata(target)
    ts = datetime.utcnow().isoformat() + "Z"
    title = f"DarkReconX Report - {target}"
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; }}
    h1 {{ color: #2b6cb0 }}
    pre {{ background: #f6f8fa; padding: 12px }}
    .section {{ margin-bottom: 20px }}
    .small {{ color: #666; font-size: 0.9em }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p class="small">Generated: {ts}</p>
  <div class="section">
    <h2>Summary</h2>
    <p>Confidence: {profile.get('confidence', 'N/A')}</p>
    <p>Modules: {', '.join(meta.get('modules', []))}</p>
  </div>
  <div class="section">
    <h2>Collections</h2>
    <h3>Domains</h3>
    <pre>{profile.get('domains', [])}</pre>
    <h3>IPs</h3>
    <pre>{profile.get('ips', [])}</pre>
    <h3>Emails</h3>
    <pre>{profile.get('emails', [])}</pre>
  </div>
  <div class="section">
    <h2>Notes</h2>
    <pre>{(get_profile_dir(target) / 'notes.md').read_text(encoding='utf-8') if (get_profile_dir(target) / 'notes.md').exists() else ''}</pre>
  </div>
</body>
</html>
"""
    output.write_text(html, encoding="utf-8")
    return output
