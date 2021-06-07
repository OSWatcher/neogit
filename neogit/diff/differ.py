from pathlib import Path
from typing import Iterator, List, Union

from neo4j import Record, Result, Session, Transaction

from neogit.model import DiffObject, DiffStatus, Tree
from neogit.utils import cypher_unescape


def diff_trees(
    session: Union[Session, Transaction], old_tree_sha1sum: Tree, new_tree_sha1sum: Tree
) -> Iterator[DiffObject]:
    root = Path("/")
    yield from diff_trees_rec(session, root, old_tree_sha1sum, new_tree_sha1sum)


def diff_trees_rec(
    session: Union[Session, Transaction], root: Path, old_tree_sha1sum: Tree, new_tree_sha1sum: Tree
) -> Iterator[DiffObject]:
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
        new_path = root / cypher_unescape(c)
        diff_object = DiffObject(DiffStatus.NEW, new_path)
        yield diff_object
    # deleted
    for c in old_children.keys() - new_children.keys():
        new_path = root / cypher_unescape(c)
        diff_object = DiffObject(DiffStatus.DEL, new_path)
        yield diff_object
    # modified ?
    for c in new_children.keys() & old_children.keys():
        new_path = root / cypher_unescape(c)
        if new_children[c][0] != old_children[c][0]:
            # type change
            diff_object = DiffObject(DiffStatus.TYP, new_path)
            yield diff_object
        else:
            old_sha1 = old_children[c][1]
            new_sha1 = new_children[c][1]
            if old_sha1 != new_sha1:
                diff_object = DiffObject(DiffStatus.MOD, new_path)
                yield diff_object
                if new_children[c][0] == "HAS_CHILD_TREE":
                    # recurse
                    yield from diff_trees_rec(session, new_path, old_sha1, new_sha1)
