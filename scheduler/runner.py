"""Scheduler runner skeleton.

This file provides a minimal scheduler API used by the CLI or systemd/cron to
kick off scheduled scans. It uses asyncio and optionally APScheduler when
available. The implementation here is intentionally small and safe.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable, Dict


async def run_profile_now(profile: Dict[str, Any]):
    """Execute a profile immediately.

    profile: {"name": str, "target": str, "type": "asr|subdomain|full", ...}
    """
    # In the real system we'd call the orchestrator; here we simulate with a sleep
    target = profile.get("target")
    print(f"[scheduler] running profile {profile.get('name')} for {target}")
    await asyncio.sleep(0.1)
    # Write a small marker
    os.makedirs("results/scheduler", exist_ok=True)
    with open(f"results/scheduler/{profile.get('name')}_{target}.txt", "w") as fh:
        fh.write("ran")
    return {"status": "ok", "target": target}


def schedule_periodic(profile: Dict[str, Any], interval_seconds: int, loop: asyncio.AbstractEventLoop | None = None):
    """Schedule a coroutine to run periodically on the given loop.

    This is intentionally simple: it uses create_task and sleeps in a loop.
    For production use prefer APScheduler, RQ scheduler, or Kubernetes cronjobs.
    """
    loop = loop or asyncio.get_event_loop()

    async def _runner():
        while True:
            try:
                await run_profile_now(profile)
            except Exception as e:
                print(f"[scheduler] profile {profile.get('name')} failed: {e}")
            await asyncio.sleep(interval_seconds)

    loop.create_task(_runner())
