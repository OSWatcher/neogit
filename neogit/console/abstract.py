from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path


class TaskPool(Enum):
    SHA1 = auto()
    Storage = auto()


class AbstractConsoleAdapter(ABC):
    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def increase_main_bar_total(self):
        """Increases the main bar progress bar total"""
        pass

    @abstractmethod
    def advance_main_bar_progress(self):
        """Advance the main progress bar by 1 unit"""
        pass

    @abstractmethod
    def set_pool_task(self, pool: TaskPool, filepath: Path, size: int):
        """Update the per-thread task information associated with the pool. Create the task if necessary"""
        pass

    @abstractmethod
    def update_pool_task(self, pool: TaskPool, advance: int):
        """Advance the per-thread task associated with the pool"""
        pass
