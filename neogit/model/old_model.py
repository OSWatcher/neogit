from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional


@dataclass
class DirInfo:
    dir: Path
    files: List[str]
    subdirs: List[str]


class DiffStatus(Enum):
    NEW = auto()
    # filetype change
    TYP = auto()
    MOD = auto()
    DEL = auto()


@dataclass
class FSDiffObject:
    status: DiffStatus
    is_dir: bool
    path: Path
    old_sha1sum: Optional[str]
    new_sha1sum: Optional[str]


# fs search


class FSSearchType(Enum):
    Filename = auto()
    Path = auto()
    SHA1 = auto()


@dataclass
class FSSearchResult:
    commit_name: str
    commit_sha1: str
    filepath: str
    file_sha1: str
