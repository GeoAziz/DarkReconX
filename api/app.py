"""Minimal FastAPI scaffold for DarkReconX

This module provides a lightweight HTTP API with token auth and a few endpoints
used by the CLI and scheduler. It has a runtime guard so tests can be skipped
when FastAPI isn't installed in the environment.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastapi import Depends, FastAPI, Header, HTTPException  # type: ignore
    from fastapi.responses import PlainTextResponse, Response  # type: ignore
    from pydantic import BaseModel  # type: ignore

try:
    from fastapi import Depends, FastAPI, Header, HTTPException  # type: ignore
    from fastapi.responses import PlainTextResponse, Response  # type: ignore
    from pydantic import BaseModel  # type: ignore

    fastapi_available = True
except Exception:  # pragma: no cover - tests skip if missing
    fastapi_available = False
    # Type stubs for when FastAPI isn't installed
    FastAPI = None  # type: ignore
    Header = None  # type: ignore
    HTTPException = None  # type: ignore
    Depends = None  # type: ignore
    BaseModel = None  # type: ignore
    PlainTextResponse = None  # type: ignore
    Response = None  # type: ignore

API_TOKEN = os.environ.get("DARKRECONX_API_TOKEN", "devtoken")


if fastapi_available:
    app = FastAPI(title="DarkReconX API")  # type: ignore

    class ScanRequest(BaseModel):  # type: ignore
        target: str
        profile: Optional[str] = None

    class GenerateReportRequest(BaseModel):  # type: ignore
        target: str
        format: Optional[str] = "json"

    def verify_token(x_api_token: Optional[str] = Header(None)):  # type: ignore
        if x_api_token != API_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid API token")  # type: ignore

    @app.post("/scan")  # type: ignore
    async def scan_endpoint(req: ScanRequest, token: str = Depends(verify_token)):  # type: ignore
        # In a full implementation this would enqueue a job. Here we simulate.
        job_id = str(uuid.uuid4())
        # Write a tiny 'queued' file in results/jobs for visibility
        os.makedirs("results/jobs", exist_ok=True)
        with open(f"results/jobs/{job_id}.json", "w") as fh:
            json.dump({"job_id": job_id, "target": req.target, "status": "queued"}, fh)
        return {"job_id": job_id, "status": "queued"}

    @app.post("/generate_report")  # type: ignore
    async def generate_report(req: GenerateReportRequest, token: str = Depends(verify_token)):  # type: ignore
        """Generate a report for a target by reading existing result files and
        passing them to the reports generator. Returns a URL path to retrieve
        the generated report.
        """
        import asyncio as _asyncio

        import reports.generator as _rg

        target = req.target
        fmt = (req.format or "json").lower()
        # Try to load existing result JSON (sync read in thread)
        candidates = [f"results/{target}.json", f"results/{target}_async.json"]

        def _load():
            for p in candidates:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as fh:
                        try:
                            return json.load(fh)
                        except Exception:
                            return None
            return None

        unified = await _asyncio.to_thread(_load)
        if unified is None:
            raise HTTPException(status_code=404, detail="Source results not found for target")  # type: ignore

        # Generate report off the event loop to avoid blocking
        def _gen():
            return _rg.generate(target, unified, format=fmt)

        path = await _asyncio.to_thread(_gen)
        # Return a simple API path to fetch the report
        return {"status": "ok", "report": f"/reports/{target}?format={fmt}"}

    @app.get("/results/{target}")  # type: ignore
    async def get_results(target: str, token: str = Depends(verify_token)):  # type: ignore
        # Try known result filenames
        candidates = [f"results/{target}.json", f"results/{target}_async.json", f"results/{target}.txt"]
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r") as fh:
                        # attempt to parse JSON, if not return raw text
                        try:
                            return json.load(fh)
                        except Exception:
                            return {"raw": fh.read()}
                except Exception:
                    raise HTTPException(status_code=500, detail="Failed to read result file")  # type: ignore
        raise HTTPException(status_code=404, detail="Results for target not found")  # type: ignore

    @app.get("/history")  # type: ignore
    async def get_history(token: str = Depends(verify_token)):  # type: ignore
        # List result files briefly
        out = []
        for root, _, files in os.walk("results"):
            for f in files:
                if f.endswith((".json", ".txt")):
                    out.append(os.path.relpath(os.path.join(root, f)))
        return {"files": sorted(out)}

    @app.get("/reports/{target}")  # type: ignore
    async def get_report(target: str, format: str = "json", download: bool = False, token: str = Depends(verify_token)):  # type: ignore
        """Serve generated report files for a target.

        format: one of 'json', 'csv', 'md'
        This performs async-safe file reads using asyncio.to_thread to avoid blocking.
        """
        import asyncio as _asyncio

        from fastapi.responses import PlainTextResponse, Response  # type: ignore

        reports_dir = os.path.join("results", "reports")
        ext = format.lower()
        if ext not in ("json", "csv", "md"):
            raise HTTPException(status_code=400, detail="Unsupported report format")  # type: ignore

        fname = os.path.join(reports_dir, f"{target}.{ext}")
        if not os.path.exists(fname):
            raise HTTPException(status_code=404, detail="Report not found")  # type: ignore

        # Read file off the event loop
        def _read():
            with open(fname, "rb") as fh:
                return fh.read()

        content = await _asyncio.to_thread(_read)

        # Return JSON decoded object for json, else plain text
        text = content.decode("utf-8")
        filename = f"{target}.{ext}"
        if ext == "json":
            try:
                obj = json.loads(text)
                if download:
                    return Response(
                        json.dumps(obj),
                        media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                    )
                return obj
            except Exception:
                # If the file contains non-json, return raw
                return PlainTextResponse(
                    text,
                    media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'} if download else None,
                )
        elif ext == "csv":
            return PlainTextResponse(
                text,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'} if download else None,
            )
        else:
            return PlainTextResponse(
                text,
                media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'} if download else None,
            )

else:  # pragma: no cover - no fastapi installed in test env
    # Provide helpful placeholders if FastAPI isn't available so imports don't crash
    def _missing(*a, **k):
        raise RuntimeError("FastAPI is not installed. Install fastapi to enable the API.")

    app = _missing
