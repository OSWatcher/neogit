from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from neo4j import Record, Result, Session, Transaction


@dataclass(init=False)
class Blob:
    sha1sum: str


@dataclass(init=False)
class Tree:
    sha1sum: str
    children_blob: Dict[str, Blob]
    children_tree: Dict[str, "Tree"]

    def __init__(self):
        self.children_tree = {}
        self.children_blob = {}

    def create(self, session: Union[Session, Transaction]):
        # explore dfs tree
        for tree in self.children_tree.values():
            tree.create(session)
        # create child blobs
        query = """
        UNWIND $unwind_param as blob
        MERGE (b:Blob {sha1sum: blob})
        """
        blob_list = [b.sha1sum for b in self.children_blob.values()]
        # from IPython import embed
        # embed()
        session.run(query, {"unwind_param": blob_list})
        # create child trees
        query = """
        UNWIND $unwind_param as tree
        MERGE (t:Tree {sha1sum: tree})
        """
        tree_list = [t.sha1sum for t in self.children_tree.values()]
        session.run(query, {"unwind_param": tree_list})
        # create parent
        query = """
        MERGE (p:Tree {sha1sum: $sha1sum})
        """
        session.run(query, {"sha1sum": self.sha1sum})
        # create blob relationship
        # [{"name": "xxx", "sha1sum: "xxxx"
        rel_list = [{"name": filename, "sha1sum": blob.sha1sum} for filename, blob in self.children_blob.items()]
        query = """
        MATCH (p:Tree {sha1sum: $parent_sha1})
        WITH p
        UNWIND $unwind_param as rel
        MATCH (c:Blob {sha1sum: rel.sha1sum})
        MERGE (p)-[:HAS_CHILD_BLOB {name: rel.name}]->(c)
        """
        session.run(query, {"parent_sha1": self.sha1sum, "unwind_param": rel_list})
        # create Tree relationship
        rel_list = [{"name": filename, "sha1sum": tree.sha1sum} for filename, tree in self.children_tree.items()]
        query = """
        MATCH (p:Tree {sha1sum: $parent_sha1})
        WITH p
        UNWIND $unwind_param as rel
        MATCH (c:Tree {sha1sum: rel.sha1sum})
        MERGE (p)-[:HAS_CHILD_TREE {name: rel.name}]->(c)
        """
        session.run(query, {"parent_sha1": self.sha1sum, "unwind_param": rel_list})


@dataclass(init=False)
class Commit:
    sha1sum: str
    name: str
    date: str
    filesystem: Tree
    previous_commit: "Commit"

    def __init__(self, session: Union[Session, Transaction], name: str, sha1sum: str, date: str):
        self.session = session
        self.name = name
        self.sha1sum = sha1sum
        self.date = date

    def create(self):
        query = """
        MERGE (o:Commit {sha1sum: $sha1sum, name: $name, date: $date})
        RETURN o
        """
        cursor = self.session.run(query, {"sha1sum": self.sha1sum, "name": self.name, "date": self.date})
        return True if cursor.single() is not None else False

    def add_filesystem(self, filesystem: Tree):
        query = """
        MATCH (o:Commit {sha1sum: $comm_sha1sum}), (t:Tree {sha1sum: $tree_sha1sum})
        Merge (o)-[:OWNS_FILESYSTEM]->(t)
        RETURN o
        """
        self.session.run(query, {"comm_sha1sum": self.sha1sum, "tree_sha1sum": filesystem.sha1sum})

    def add_previous(self, previous_node: "Commit"):
        query = """
        MATCH (o:Commit), (p:Commit)
        WHERE o.sha1sum = $current_sha1 AND p.sha1sum = $previous_sha1
        MERGE (o)-[:HAS_PREVIOUS]->(p)
        """
        params = {"current_sha1": self.sha1sum, "previous_sha1": previous_node.sha1sum}
        self.session.run(query, params)


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
