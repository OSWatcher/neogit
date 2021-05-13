from abc import ABC, abstractmethod
from pathlib import Path


class AbstractConsoleAdapter(ABC):
    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def set_sha1_task(self, filepath: Path, size: int):
        """Update the per-thread task information associated with the SHA1 pool. Create the task if necessary"""
        pass

    @abstractmethod
    def update_sha1_task(self, advance: int):
        """Advance the per-thread task associated with the SHA1 pool"""
        pass
