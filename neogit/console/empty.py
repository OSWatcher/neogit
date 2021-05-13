from pathlib import Path

from .abstract import AbstractConsoleAdapter


class EmptyConsoleAdapter(AbstractConsoleAdapter):
    """This adapter will simply ignore any console output"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_sha1_task(self, filepath: Path, size: int):
        pass

    def update_sha1_task(self, advance: int):
        pass
