from pathlib import Path

from . import TaskPool
from .abstract import AbstractConsoleAdapter


class EmptyConsoleAdapter(AbstractConsoleAdapter):
    """This adapter will simply ignore any console output"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def increase_main_bar_total(self):
        pass

    def advance_main_bar_progress(self):
        pass

    def set_pool_task(self, pool: TaskPool, filepath: Path, size: int):
        pass

    def update_pool_task(self, pool: TaskPool, advance: int):
        pass
