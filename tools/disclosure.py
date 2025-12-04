import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def create_disclosure_package(target, findings, reporter_name, contact):
    """Create a disclosure package (md) containing executive summary and technical findings."""
    tpl = env.get_template("disclosure_email.md.j2")
    payload = {
        "target": target,
        "findings": findings,
        "reporter": reporter_name,
        "contact": contact,
        "date": datetime.utcnow().isoformat() + "Z",
    }
    return tpl.render(payload)


def save_package(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path
