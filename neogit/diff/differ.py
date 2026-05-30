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

# One-sided traversal: every descendant (Tree and Blob) of a subtree, with its path.
_SUBTREE_QUERY = """
MATCH path = (t:Tree {hash: $hash})-[:HAS_CHILD_TREE|HAS_CHILD_BLOB*]->(n)
RETURN [r IN relationships(path) | r.name] AS parts, labels(n) AS labels, n.hash AS hash
"""


def diff_trees(
    session: Union[Session, Transaction],
    old_tree_sha1sum: str,
    new_tree_sha1sum: str,
    root: Path = ROOT_PATH,
    recursive: bool = False,
) -> Iterator[FSDiffObject]:
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
            if is_dir and recursive:
                yield from _iter_subtree(session, d["new_hash"], path, DiffStatus.NEW)
        elif status == "DEL":
            is_dir = d["reltype"] == "HAS_CHILD_TREE"
            yield FSDiffObject(DiffStatus.DEL, is_dir, path, d["old_hash"], None)
            if is_dir and recursive:
                yield from _iter_subtree(session, d["old_hash"], path, DiffStatus.DEL)
        else:  # MOD
            old_reltype = d["old_reltype"]
            new_reltype = d["new_reltype"]
            if old_reltype == new_reltype:
                is_dir = new_reltype == "HAS_CHILD_TREE"
                yield FSDiffObject(DiffStatus.MOD, is_dir, path, d["old_hash"], d["new_hash"])
                if is_dir and recursive:
                    yield from diff_trees(session, d["old_hash"], d["new_hash"], path, recursive)
            else:
                # Type change (file <-> directory): emit a delete of the old node and a
                # create of the new one, expanding whichever side is a directory.
                # TODO: a dedicated DiffStatus.TYP could represent this more precisely.
                old_is_dir = old_reltype == "HAS_CHILD_TREE"
                yield FSDiffObject(DiffStatus.DEL, old_is_dir, path, d["old_hash"], None)
                if old_is_dir and recursive:
                    yield from _iter_subtree(session, d["old_hash"], path, DiffStatus.DEL)
                new_is_dir = new_reltype == "HAS_CHILD_TREE"
                yield FSDiffObject(DiffStatus.NEW, new_is_dir, path, None, d["new_hash"])
                if new_is_dir and recursive:
                    yield from _iter_subtree(session, d["new_hash"], path, DiffStatus.NEW)


def _iter_subtree(
    session: Union[Session, Transaction],
    tree_sha1sum: str,
    base_path: Path,
    status: DiffStatus,
) -> Iterator[FSDiffObject]:
    """Yield every descendant of a subtree as NEW or DEL (used for added/removed dirs)."""
    records: List[Record] = list(session.run(_SUBTREE_QUERY, parameters={"hash": tree_sha1sum}))
    for record in records:
        parts = [cypher_unescape(p) for p in record["parts"]]
        node_path = base_path.joinpath(*parts)
        is_dir = "Tree" in record["labels"]
        if status == DiffStatus.NEW:
            yield FSDiffObject(DiffStatus.NEW, is_dir, node_path, None, record["hash"])
        else:
            yield FSDiffObject(DiffStatus.DEL, is_dir, node_path, record["hash"], None)
