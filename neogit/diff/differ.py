from pathlib import Path
from typing import Iterator, List, Union

from neo4j import Record, Result, Session, Transaction

from neogit.model import DiffStatus, FSDiffObject
from neogit.utils import cypher_unescape

ROOT_PATH = Path("/")


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
    # query their children
    query = """
    MATCH (new_tree:Tree {sha1sum: $new_tree_sha1})-[r_new:HAS_CHILD_TREE|HAS_CHILD_BLOB]->(new_child)
    WITH apoc.map.fromLists(collect(r_new.name), collect([type(r_new), new_child.sha1sum])) as new
    MATCH (old_tree:Tree {sha1sum: $old_tree_sha1})-[r_old:HAS_CHILD_TREE|HAS_CHILD_BLOB]->(old_child)
    RETURN new, apoc.map.fromLists(collect(r_old.name), collect([type(r_old), old_child.sha1sum])) as old
    """
    cursor: Result = session.run(
        query, parameters={"new_tree_sha1": new_tree_sha1sum, "old_tree_sha1": old_tree_sha1sum}
    )
    records: List[Record] = list(cursor)
    if not records:
        return
    record: Record = records[0]
    new_children = record["new"]
    old_children = record["old"]

    # created children
    for c in new_children.keys() - old_children.keys():
        reltype, sha1sum = new_children[c]
        is_dir = True if reltype == "HAS_CHILD_TREE" else False
        new_path = root / cypher_unescape(c)
        diff_object = FSDiffObject(DiffStatus.NEW, is_dir, new_path, sha1sum)
        yield diff_object
    # deleted
    for c in old_children.keys() - new_children.keys():
        reltype, sha1sum = old_children[c]
        sha1sum = old_children[c][1]
        is_dir = True if reltype == "HAS_CHILD_TREE" else False
        new_path = root / cypher_unescape(c)
        diff_object = FSDiffObject(DiffStatus.DEL, is_dir, new_path, sha1sum)
        yield diff_object
    # modified ?
    for c in new_children.keys() & old_children.keys():
        new_path = root / cypher_unescape(c)
        if new_children[c][0] != old_children[c][0]:
            # type change
            raise NotImplementedError("Type change diff is not implemented")
            # diff_object = FSDiffObject(DiffStatus.TYP, new_path)
            # yield diff_object
        else:
            old_reltype, old_sha1sum = old_children[c]
            new_reltype, new_sha1sum = new_children[c]
            is_dir = True if new_reltype == "HAS_CHILD_TREE" else False
            if old_sha1sum != new_sha1sum:
                diff_object = FSDiffObject(DiffStatus.MOD, is_dir, new_path, new_sha1sum)
                yield diff_object
                if new_reltype == "HAS_CHILD_TREE" and recursive:
                    yield from diff_trees(session, old_sha1sum, new_sha1sum, new_path, recursive)
