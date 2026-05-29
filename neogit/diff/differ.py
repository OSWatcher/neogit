# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from typing import Iterator, List, Union

from neo4j import Record, Result, Session, Transaction

from neogit.model import DiffStatus, FSDiffObject
from neogit.utils import cypher_unescape

ROOT_PATH = Path("/")

# Single-level diff of two Trees, keyed by the relationship `name` (path-aware).
# Anchoring both trees with MATCH {hash} makes it robust to empty trees; no APOC required.
_SINGLE_LEVEL_QUERY = """
MATCH (old:Tree {hash: $old})
MATCH (new:Tree {hash: $new})

OPTIONAL MATCH (new)-[r_new]->(c_new)
WHERE NOT EXISTS((old)-[{name: r_new.name}]->())
WITH old, new, collect(CASE WHEN c_new IS NOT NULL
     THEN {status: 'NEW', name: r_new.name, reltype: type(r_new),
           old_hash: null, new_hash: c_new.hash}
     END) AS created

OPTIONAL MATCH (old)-[r_del]->(c_del)
WHERE NOT EXISTS((new)-[{name: r_del.name}]->())
WITH old, new, created, collect(CASE WHEN c_del IS NOT NULL
     THEN {status: 'DEL', name: r_del.name, reltype: type(r_del),
           old_hash: c_del.hash, new_hash: null}
     END) AS deleted

OPTIONAL MATCH (old)-[r_o]->(c_o)
OPTIONAL MATCH (new)-[r_n {name: r_o.name}]->(c_n)
WHERE c_n IS NOT NULL AND c_o.hash <> c_n.hash
WITH created, deleted, collect(CASE WHEN c_o IS NOT NULL AND c_n IS NOT NULL
     THEN {status: 'MOD', name: r_o.name,
           old_reltype: type(r_o), new_reltype: type(r_n),
           old_hash: c_o.hash, new_hash: c_n.hash}
     END) AS changed

UNWIND created + deleted + changed AS d
WITH d WHERE d IS NOT NULL
RETURN d
"""


def diff_trees(
    session: Union[Session, Transaction],
    old_tree_sha1sum: str,
    new_tree_sha1sum: str,
    root: Path = ROOT_PATH,
    recursive: bool = False,
) -> Iterator[FSDiffObject]:
    # NOTE: `recursive` is accepted for API stability but is a no-op here;
    # subtree expansion/recursion is wired in a follow-up change.
    # stop if both trees are identical
    if old_tree_sha1sum == new_tree_sha1sum:
        return
    cursor: Result = session.run(_SINGLE_LEVEL_QUERY, parameters={"old": old_tree_sha1sum, "new": new_tree_sha1sum})
    # materialize before issuing further queries on the same session
    records: List[Record] = list(cursor)
    for record in records:
        d = record["d"]
        path = root / cypher_unescape(d["name"])
        status = d["status"]
        if status == "NEW":
            is_dir = d["reltype"] == "HAS_CHILD_TREE"
            yield FSDiffObject(DiffStatus.NEW, is_dir, path, None, d["new_hash"])
        elif status == "DEL":
            is_dir = d["reltype"] == "HAS_CHILD_TREE"
            yield FSDiffObject(DiffStatus.DEL, is_dir, path, d["old_hash"], None)
        else:  # MOD
            is_dir = d["new_reltype"] == "HAS_CHILD_TREE"
            yield FSDiffObject(DiffStatus.MOD, is_dir, path, d["old_hash"], d["new_hash"])
