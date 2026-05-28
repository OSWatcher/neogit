# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from pathlib import Path


class AbstractConsoleAdapter(ABC):
    """Console adapter for live progress display during ``neogit commit``.

    Adapters are used as context managers. Hook methods may be called from
    background threads (the single hasher/visitor thread, the N uploader
    pool threads, the main thread for Cypher merges) and implementations
    must be thread-safe.
    """

    @abstractmethod
    def __enter__(self) -> "AbstractConsoleAdapter":
        ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

    # Hashing stage (fired from the main thread, consuming visitor.as_gen())
    @abstractmethod
    def on_file_hashed(self, path: Path) -> None:
        ...

    @abstractmethod
    def on_dir_merkelized(self, path: Path) -> None:
        ...

    # Cypher merge stage (fired from the main thread)
    @abstractmethod
    def on_tree_merged(self) -> None:
        ...

    # Upload stage (fired from N uploader pool threads)
    @abstractmethod
    def on_upload_started(self, worker_id: int, path: Path, size: int) -> None:
        ...

    @abstractmethod
    def on_upload_progress(self, worker_id: int, advance: int) -> None:
        ...

    @abstractmethod
    def on_upload_finished(self, worker_id: int, was_skipped: bool) -> None:
        ...
