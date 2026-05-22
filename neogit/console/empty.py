from pathlib import Path

from .abstract import AbstractConsoleAdapter


class EmptyConsoleAdapter(AbstractConsoleAdapter):
    """No-op adapter used when ``--gui`` is off."""

    def __enter__(self) -> "EmptyConsoleAdapter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def on_file_hashed(self, path: Path) -> None:
        pass

    def on_dir_merkelized(self, path: Path) -> None:
        pass

    def on_tree_merged(self) -> None:
        pass

    def on_upload_started(self, worker_id: int, path: Path, size: int) -> None:
        pass

    def on_upload_progress(self, worker_id: int, advance: int) -> None:
        pass

    def on_upload_finished(self, worker_id: int, was_skipped: bool) -> None:
        pass
