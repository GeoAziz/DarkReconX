import csv
import json
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
# Prefer a results/reports directory inside the current working directory when
# running under tests (they typically create a tmp cwd). Fall back to the
# package-relative results/reports directory for normal usage.
_PACKAGE_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "reports")
_CWD_OUT_DIR = os.path.join(os.getcwd(), "results", "reports")
OUT_DIR = _CWD_OUT_DIR if os.path.isdir(os.path.join(os.getcwd(), "results")) else _PACKAGE_OUT_DIR
os.makedirs(OUT_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def _save_json(target, data):
    path = os.path.join(OUT_DIR, f"{target}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return path


def _save_csv(target, data):
    path = os.path.join(OUT_DIR, f"{target}.csv")
    # flatten assuming unified_result is list of records
    records = data if isinstance(data, list) else [data]
    if not records:
        return path
    keys = sorted({k for r in records for k in r.keys()})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in keys})
    return path


def _save_md(target, data):
    tpl = env.get_template("report_default.md.j2")
    md = tpl.render(target=target, generated_at=datetime.utcnow().isoformat() + "Z", data=data)
    path = os.path.join(OUT_DIR, f"{target}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return path


def generate(target: str, unified_result, format: str = "md") -> str:
    """Generate a per-target report in the requested format and return path."""
    if format == "json":
        return _save_json(target, unified_result)
    elif format == "csv":
        return _save_csv(target, unified_result)
    else:
        return _save_md(target, unified_result)


def generate_summary(results_list, out_path=None):
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "tool_version": "DarkReconX-0.1",
        "count": len(results_list),
        "top_risks": {},
    }
    # Compute top risks
    risk_counts = {}
    for r in results_list:
        for reason in r.get("risk", {}).get("reasons", []):
            risk_counts[reason] = risk_counts.get(reason, 0) + 1
    out["top_risks"] = sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)
    if not out_path:
        out_path = os.path.join(OUT_DIR, "summary.md")
    tpl = env.get_template("summary.md.j2")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(tpl.render(summary=out))
    return out_path
