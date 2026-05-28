# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
from enum import Enum, auto
from functools import lru_cache
from typing import Dict, List

from attrs import define, field, validators

# avoid circular dependency
from .node import Node


class MerkleLabel(Enum):
    # this is used to differentiate between MerkleNode who are blobs and empty Trees
    # since both have no children
    Blob = auto()
    Tree = auto()


@lru_cache(maxsize=1)
def get_all_hash_digest_len() -> List[int]:
    # init hashes
    hash_funcs = [hashlib.sha1(), hashlib.sha256(), hashlib.sha512()]
    # captures digest for empty string
    hash_digests_len: List[int] = [len(h.hexdigest()) for h in hash_funcs]
    return hash_digests_len


@define(auto_attribs=True)
class MerkleNode(Node):
    """Represents a merkelized Node"""

    """The hexdigest of a hashing algorithm (SHA1, SHA256, SHA512)"""
    hash: str = field()
    # label to differentiate Blob from Trees
    label: MerkleLabel = field(validator=validators.in_(MerkleLabel))
    # TODO: use iter_child_nodes
    children: Dict[str, "MerkleNode"] = field(factory=dict)

    @hash.validator
    def validate_hash(self, attribute, value: str):
        """Validate that hash string is a real hash (SHA1, SHA256, SHA512)"""
        # try to match hash
        for hash_digest_len in get_all_hash_digest_len():
            # Note: for the f-string, we have to triple the curly braces
            # second level: actually print the curly braces
            # third level: interpolate the variable inside
            if re.match(rf"[0-9a-fA-F]{{{hash_digest_len}}}", value):
                return
        raise ValueError(f"Received hash {value} is not a SHA1, SHA256 or SHA512 hexdigest")
