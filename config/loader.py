import yaml
from pathlib import Path


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
