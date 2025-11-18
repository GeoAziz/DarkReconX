import pkgutil
import importlib
import inspect
from pathlib import Path
from typing import Dict, Type, List

from core.module import BaseModule


def _modules_path() -> Path:
    return Path(__file__).resolve().parents[1] / "modules"


def discover_modules() -> Dict[str, Type[BaseModule]]:
    """Discover modules under the top-level `modules/` directory.

    Returns a mapping of module_name -> ModuleClass (subclass of BaseModule).
    """
    modules_dir = _modules_path()
    found: Dict[str, Type[BaseModule]] = {}

    # find top-level .py files in modules/ and subpackages with scanner.py
    for entry in modules_dir.iterdir():
        if entry.is_dir():
            # look for scanner.py inside the package
            mod_name = entry.name
            candidate = f"modules.{mod_name}.scanner"
            try:
                mod = importlib.import_module(candidate)
            except Exception:
                # skip modules that fail to import
                continue
        elif entry.is_file() and entry.suffix == ".py":
            mod_name = entry.stem
            candidate = f"modules.{mod_name}"
            try:
                mod = importlib.import_module(candidate)
            except Exception:
                continue
        else:
            continue

        # inspect for BaseModule subclasses defined in that module
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            try:
                if issubclass(obj, BaseModule) and obj is not BaseModule:
                    # prefer class attribute name or module filename
                    name = getattr(obj, "name", None) or mod_name
                    found[name] = obj
            except Exception:
                continue

    return found


def load_module(name: str, **kwargs) -> BaseModule:
    """Load and instantiate a module by name (as discovered by discover_modules).

    Raises KeyError if module not found.
    """
    mods = discover_modules()
    cls = mods.get(name)
    if cls is None:
        raise KeyError(f"Module not found: {name}")
    return cls(**kwargs)