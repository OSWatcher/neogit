import logging
import os
from abc import ABC
from pathlib import Path
from typing import Iterator

from attrs import define

# avoid circular dependency
from .node import Node


@define(auto_attribs=True)
class FSNode(Node, ABC):
    path: Path


@define(auto_attribs=True)
class FSDirectoryNode(FSNode):
    def validate_path(self, attribute, value):
        if not value.is_dir():
            raise ValueError(f"Path {value} is not a directory")

    def iter_child_nodes(self) -> Iterator[FSNode]:
        if self.path.is_dir() and not self.path.is_symlink():
            try:
                with os.scandir(self.path) as scan_it:
                    for entry in scan_it:
                        entry_path = self.path / entry.name
                        if entry.is_dir(follow_symlinks=False):
                            yield FSDirectoryNode(entry_path)
                        else:
                            yield FSFileNode(entry_path)
            # TODO: how to put try except only on with statement ?
            except OSError as e:
                # log warning and return
                logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
                logger.warning("SKIP: %s (%s)", self.path, e)


@define(auto_attribs=True)
class FSFileNode(FSNode):
    def validate_path(self, attribute, value):
        if value.is_dir():
            raise ValueError(f"Path {value} should not be a directory")
