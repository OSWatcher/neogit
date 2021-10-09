import hashlib
import re
from functools import lru_cache
from typing import Dict, List

import attr

# avoid circular dependency
from .node import Node


@lru_cache(maxsize=1)
def get_all_hash_digest_len() -> List[int]:
    # init hashes
    hash_funcs = [hashlib.sha1(), hashlib.sha256(), hashlib.sha512()]
    # captures digest for empty string
    hash_digests_len: List[int] = [len(h.hexdigest()) for h in hash_funcs]
    return hash_digests_len


@attr.s
class MerkleNode(Node):
    """Represents a merkelized Node"""

    """The hexdigest of a hashing algorithm (SHA1, SHA256, SHA512)"""
    hash: str = attr.ib()
    children: Dict[str, "MerkleNode"] = attr.ib(factory=dict)

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
