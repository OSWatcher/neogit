from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

from neo4j import Record, Result, Session, Transaction


@dataclass(init=False)
class Blob:
    hash: str


@dataclass(init=False)
class Tree:
    hash: str
    children_blob: Dict[str, Blob]
    children_tree: Dict[str, "Tree"]

    def __init__(self):
        self.children_tree = {}
        self.children_blob = {}

    def create_rec(self, session: Union[Session, Transaction]):
        """Create the Tree recursively"""
        # explore
        for tree in self.children_tree.values():
            tree.create_partial(session)

    def create_partial(self, session: Union[Session, Transaction]):
        """Create the Tree partially"""
        # create child blobs
        query = """
        UNWIND $unwind_param as blob
        MERGE (b:Blob {hash: blob})
        """
        blob_list = [b.hash for b in self.children_blob.values()]
        # from IPython import embed
        # embed()
        session.run(query, {"unwind_param": blob_list})
        # create child trees
        query = """
        UNWIND $unwind_param as tree
        MERGE (t:Tree {hash: tree})
        """
        tree_list = [t.hash for t in self.children_tree.values()]
        session.run(query, {"unwind_param": tree_list})
        # create parent
        query = """
        MERGE (p:Tree {hash: $hash})
        """
        session.run(query, {"hash": self.hash})
        # create blob relationship
        # [{"name": "xxx", "hash: "xxxx"
        rel_list = [{"name": filename, "hash": blob.hash} for filename, blob in self.children_blob.items()]
        query = """
        MATCH (p:Tree {hash: $parent_sha1})
        WITH p
        UNWIND $unwind_param as rel
        MATCH (c:Blob {hash: rel.hash})
        MERGE (p)-[:HAS_CHILD_BLOB {name: rel.name}]->(c)
        """
        session.run(query, {"parent_sha1": self.hash, "unwind_param": rel_list})
        # create Tree relationship
        rel_list = [{"name": filename, "hash": tree.hash} for filename, tree in self.children_tree.items()]
        query = """
        MATCH (p:Tree {hash: $parent_sha1})
        WITH p
        UNWIND $unwind_param as rel
        MATCH (c:Tree {hash: rel.hash})
        MERGE (p)-[:HAS_CHILD_TREE {name: rel.name}]->(c)
        """
        session.run(query, {"parent_sha1": self.hash, "unwind_param": rel_list})

    def has_child_tree(self, session: Union[Session, Transaction], tree_name: str) -> "Tree":
        query = """
        MATCH (p:Tree {hash: $hash})-[r:HAS_CHILD_TREE]->(t:Tree)
        WHERE r.name = $tree_name
        RETURN t
        """
        cursor = session.run(query, {"hash": self.hash, "tree_name": tree_name})
        record_list = list(cursor)
        if not record_list:
            raise RuntimeError(f"Tree {self.hash}: No child tree for filename {tree_name}")
        record = record_list[0]
        tree = Tree()
        tree.hash = record["t"]["hash"]
        return tree

    def get_children(self, session: Union[Session, Transaction]):
        query = """
        MATCH (p:Tree {hash: $hash})-[r]->(c)
        return r.name, c.hash, labels(c)[0]
        """
        cursor = session.run(query, {"hash": self.hash})
        for record in cursor:
            filename, child_hash, child_type = record
            esc_filename = filename
            if child_type == "Blob":
                b = Blob()
                b.hash = child_hash
                self.children_blob[esc_filename] = b
            elif child_type == "Tree":
                t = Tree()
                t.hash = child_hash
                self.children_tree[esc_filename] = t
            else:
                raise RuntimeError(f"Unexpected child label {child_type}")


@dataclass(init=False)
class Commit:
    name: str
    hash: str
    date: str
    filesystem: Tree
    previous_commit: "Commit"

    def __init__(self, session: Union[Session, Transaction], name: str, hash: str, date: str):
        self.session = session
        self.name = name
        self.hash = hash
        self.date = date

    @staticmethod
    def iter(session: Union[Session, Transaction], branch: str) -> Iterator["Commit"]:
        """produces an iterator on all commits pointed by the branch name, from most recent to oldest"""
        query = """
        MATCH (b:Branch)-[:TRACKS_COMMIT]->(c:Commit)
        WHERE b.name = $branch_name
        OPTIONAL MATCH (c)-[:HAS_PREVIOUS*]->(p:Commit)
        RETURN c + collect(p) as commit_log
        """
        cursor = session.run(query, parameters={"branch_name": branch})
        record = list(cursor)[0]
        for commit in record["commit_log"]:
            hash = commit["hash"]
            name = commit["name"]
            date = commit["date"]
            commit_obj = Commit(session, name, hash, date)
            yield commit_obj

    @staticmethod
    def get(session: Union[Session, Transaction], hash: str) -> Optional["Commit"]:
        query = """
        MATCH (o:Commit {hash: $hash})
        RETURN o
        """
        cursor = session.run(query, {"hash": hash})
        record_list = list(cursor)
        if not record_list:
            return None
        record: Record = record_list[0]
        hash = record["o"]["hash"]
        name = record["o"]["name"]
        date = record["o"]["date"]
        commit = Commit(session, name, hash, date)
        return commit

    def owns_filesystem(self) -> Tree:
        query = """
        MATCH (o:Commit {hash: $hash})-[:OWNS_FILESYSTEM]->(t:Tree)
        RETURN t
        """
        cursor = self.session.run(query, {"hash": self.hash})
        record_list = list(cursor)
        if not record_list:
            raise RuntimeError("No filesystem associated with commit")
        record: Record = record_list[0]
        t = Tree()
        t.hash = record["t"]["hash"]
        return t

    def get_tree_sha1_from_commit_sha1(session: Union[Session, Transaction], sha1: str):
        query = """
        MATCH (c:Commit {hash: $hash})-[:OWNS_FILESYSTEM]->(t:Tree)
        RETURN t
        """
        cursor = session.run(query, {"hash": sha1})
        return list(cursor)[0]["t"]["hash"]

    def create(self):
        query = """
        MERGE (o:Commit {hash: $hash, name: $name, date: $date})
        RETURN o
        """
        cursor = self.session.run(query, {"hash": self.hash, "name": self.name, "date": self.date})
        return True if cursor.single() is not None else False

    def add_filesystem(self, filesystem: Tree):
        query = """
        MATCH (o:Commit {hash: $comm_hash}), (t:Tree {hash: $tree_hash})
        Merge (o)-[:OWNS_FILESYSTEM]->(t)
        RETURN o
        """
        self.session.run(query, {"comm_hash": self.hash, "tree_hash": filesystem.hash})

    def add_previous(self, previous_node: "Commit"):
        query = """
        MATCH (o:Commit), (p:Commit)
        WHERE o.hash = $current_sha1 AND p.hash = $previous_sha1
        MERGE (o)-[:HAS_PREVIOUS]->(p)
        """
        params = {"current_sha1": self.hash, "previous_sha1": previous_node.hash}
        self.session.run(query, params)

    def __iter__(self):
        yield self
        current: Commit = self
        while True:
            # get next commit
            query = """
            MATCH (a:Commit)-[:HAS_PREVIOUS]->(b:Commit)
            WHERE a.hash = $current_hash
            RETURN b
            """
            result: Result = self.session.run(query, parameters={"current_hash": current.hash})
            cursors = list(result)
            previous = cursors[0]
            if not previous:
                break
            previous_commit = previous["b"]
            name = previous_commit["name"]
            hash = previous_commit["hash"]
            date = previous_commit["date"]
            yield Commit(self.session, name, hash, date)


@dataclass(init=False)
class Branch:
    name: str
    commit: Commit

    def __init__(self, session: Union[Session, Transaction], branch_name: str):
        self.session = session
        self.name = branch_name

    def __bool__(self):
        query = """
        MATCH (b:Branch)
        WHERE b.name = $name
        RETURN b
        """
        cursor: Result = self.session.run(query, {"name": self.name})
        return True if cursor.single() is not None else False

    def create(self):
        query = """
        MERGE (b:Branch {name: $name})
        RETURN b
        """
        cursor: Result = self.session.run(query, {"name": self.name})
        if cursor.single() is None:
            raise RuntimeError("Failed to create object")

    @property
    def os_commit(self) -> Optional[Commit]:
        query = """
        MATCH (b:Branch {name: $name})-[:TRACKS_COMMIT]->(o:Commit)
        RETURN o
        """
        cursor: Result = self.session.run(query, {"name": self.name})
        rec_list: List[Record] = list(cursor)
        if not rec_list:
            return None
        res: Record = rec_list[0]
        name = res["o"]["name"]
        sha1sum = res["o"]["sha1sum"]
        date = res["o"]["date"]
        commit = Commit(self.session, name, sha1sum, date)
        return commit

    def set_os_commit(self, commit: "Commit"):
        query = """
        MATCH (b:Branch)-[r:TRACKS_COMMIT]->()
        WHERE b.name = $name
        DELETE r
        """
        self.session.run(query, name=self.name)
        query = """
        MATCH (b:Branch),(new_os:Commit)
        WHERE b.name = $name AND new_os.sha1sum = $sha1sum
        MERGE (b)-[:TRACKS_COMMIT]->(new_os)
        """
        params = {"name": self.name, "sha1sum": commit.sha1sum}
        self.session.run(query, params)


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
