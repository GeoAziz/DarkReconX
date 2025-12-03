import os
from pathlib import Path

import yaml


def _load_dotenv(path: Path):
    """Lightweight .env parser: read KEY=VALUE lines into os.environ if not already set."""
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and os.environ.get(k) is None:
                os.environ[k] = v
    except Exception:
        # best-effort; don't raise if .env is malformed
        return


class ConfigLoader:
    def __init__(self, path: str = None):
        if path is None:
            # default to repo-root config/default.yml
            self.path = Path(__file__).resolve().parent / "default.yml"
        else:
            self.path = Path(path)
        self.config = {}
        self.load()

    def load(self):
        if not self.path.exists():
            self.config = {}
            return
        # load environment overrides from repo-root .env if present
        repo_root = Path(__file__).resolve().parents[1]
        _load_dotenv(repo_root / ".env")
        with open(self.path, "r", encoding="utf-8") as fh:
            self.config = yaml.safe_load(fh) or {}
        # simple validation
        tor = self.config.get("tor")
        if tor is None:
            # don't raise; we'll allow default behaviors elsewhere
            return
        # ensure ports are integers
        try:
            if "socks_port" in tor:
                tor["socks_port"] = int(tor["socks_port"])
            if "control_port" in tor:
                tor["control_port"] = int(tor["control_port"])
        except Exception:
            raise ValueError("Invalid port values in tor config")

        # overlay environment variables for tor and API keys
        # Tor env vars: TOR_SOCKS_PORT, TOR_CONTROL_PORT, TOR_PASSWORD
        try:
            if os.environ.get("TOR_SOCKS_PORT"):
                tor["socks_port"] = int(os.environ.get("TOR_SOCKS_PORT"))
            if os.environ.get("TOR_CONTROL_PORT"):
                tor["control_port"] = int(os.environ.get("TOR_CONTROL_PORT"))
            if os.environ.get("TOR_PASSWORD"):
                tor["password"] = os.environ.get("TOR_PASSWORD")
        except Exception:
            # ignore parse errors
            pass

        # API keys
        vt = os.environ.get("VT_API_KEY")
        if vt:
            self.config.setdefault("virustotal", {})["api_key"] = vt

    def get(self, key: str, default=None):
        parts = key.split(".")
        cur = self.config
        for p in parts:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(p, default)
            if cur is default:
                return default
        return cur


# convenience singleton
_default_loader = None


def get_config():
    global _default_loader
    if _default_loader is None:
        _default_loader = ConfigLoader()
    return _default_loader
