from abc import ABC, abstractmethod
from typing import Any


class BaseModule(ABC):
    """Base class for DarkReconX modules.

    Modules should subclass this and implement `run`.
    Metadata fields are optional but recommended.
    """

    name: str = ""
    description: str = ""
    author: str = "DarkReconX"

    def __init__(self, **kwargs: Any):
        # store kwargs for future use; modules may accept options
        self._opts = kwargs

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute the module.

        Implementations should return a Python object representing the
        result (dict/list/etc) and may print or save output using the
        framework helpers in `core.output`.
        """
        pass
