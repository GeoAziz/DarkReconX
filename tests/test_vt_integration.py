import os

import pytest

from modules.subdomain_finder import api as api_helpers


def test_virustotal_integration_optional():
    """Optional integration test for VirusTotal.

    To run this test set the environment variables:
      RUN_API_INTEGRATION=1
      VT_API_KEY=<your_virustotal_v3_api_key>

    The test will be skipped unless RUN_API_INTEGRATION is set to '1'.
    """
    if os.environ.get("RUN_API_INTEGRATION") != "1":
        pytest.skip("Skipping networked API integration test; set RUN_API_INTEGRATION=1 to run")

    api_key = os.environ.get("VT_API_KEY")
    if not api_key:
        pytest.skip("VT_API_KEY not provided; export VT_API_KEY to run this test")

    # choose a well-known domain; the test asserts we get a dict back
    res = api_helpers.enrich_with_virustotal("example.com", api_key)
    assert isinstance(res, dict)
    # success path typically includes 'data' key
    assert ("data" in res) or ("error" in res)
