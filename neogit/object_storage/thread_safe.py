import threading
from typing import Dict

from neogit.config import ObjectConfig
from neogit.object_storage.abstract import AbstractObjectStorage


class TSObjectStorage:
    """Thread safe provider for object storage.

    Return a per-thread instance
    """

    def __init__(self, cls, config: ObjectConfig):
        self._config = config
        self._cls = cls
        self._instances: Dict[int, AbstractObjectStorage] = {}

    @property
    def instance(self):
        tid = threading.get_ident()
        try:
            inst = self._instances[tid]
        except KeyError:
            inst = self._cls(self._config)
            self._instances[tid] = inst
        return inst
