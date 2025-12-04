"""API key helpers for DarkReconX.

Small utilities to check for API keys in the environment and provide
developer-friendly messages when keys are missing.
"""
import os
from typing import Tuple


def check_api_key(env_var: str) -> Tuple[bool, str]:
    """Return (present, message). If missing, message explains skipping.

    Example:
        present, msg = check_api_key('VT_API_KEY')
    """
    val = os.environ.get(env_var)
    if val:
        return True, ""
    msg = f"✨ API key missing ({env_var}). Module skipped safely."
    return False, msg
