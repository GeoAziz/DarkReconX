import asyncio

import pytest

from engine.pipeline import run_pipeline_for_targets


class Args:
    def __init__(self, domain=None, list=None, cidr=None, subs=None):
        self.domain = domain
        self.list = list
        self.cidr = cidr
        self.subs = subs


def test_run_all_domains(tmp_path):
    targets = [f"example{i}.com" for i in range(10)]
    results = asyncio.run(run_pipeline_for_targets(targets, max_concurrent_providers=5))
    # `run_pipeline_for_targets` returns a summary dict; older tests expected
    # a list. Support both shapes here for robustness.
    if isinstance(results, dict):
        items = list(results.get("targets", {}).values())
    else:
        items = list(results)
    assert len(items) == 10
    for r in items:
        assert r is not None


def test_run_all_ips(tmp_path):
    targets = [f"192.168.1.{i}" for i in range(1, 11)]
    results = asyncio.run(run_pipeline_for_targets(targets, max_concurrent_providers=5))
    if isinstance(results, dict):
        items = list(results.get("targets", {}).values())
    else:
        items = list(results)
    assert len(items) == 10
    for r in items:
        assert r is not None
