import os
from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import Iterator

import attr

# avoid circular dependency
from .node import Node


@attr.s
class FSNode(Node, ABC):
    path: Path = attr.ib()

    @abstractmethod
    @path.validator
    def validate_path(self, attribute, value):
        pass


@attr.s
class FSDirectoryNode(FSNode):
    def validate_path(self, attribute, value):
        if not value.is_dir():
            raise ValueError(f"Path {value} is not a directory")

    def iter_child_nodes(self) -> Iterator[FSNode]:
        if self.path.is_dir():
            with os.scandir(self.path) as scan_it:
                for entry in scan_it:
                    entry_path = self.path / entry.name
                    if entry.is_dir():
                        yield FSDirectoryNode(entry_path)
                    else:
                        yield FSFileNode(entry_path)


@attr.s
class FSFileNode(FSNode):
    def validate_path(self, attribute, value):
        if value.is_dir():
            raise ValueError(f"Path {value} should not be a directory")

    def hashable_data(self) -> Iterator[bytes]:
        # file, return content
        with open(self.path, "rb") as f:
            read_block = partial(f.read, 4096)
            yield from iter(read_block, b"")
