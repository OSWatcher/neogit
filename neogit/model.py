from py2neo.ogm import Model, Property, RelatedTo


class BlobNode(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()


class TreeNode(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()
    children_blobs = RelatedTo("BlobNode", "HAS_CHILD_BLOB")
    children_trees = RelatedTo("TreeNode", "HAS_CHILD_TREE")


class CommitNode(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()
    name = Property()
    filesystem = RelatedTo("TreeNode", "HAS_FILESYSTEM")
    previous_commit = RelatedTo("CommitNode", "HAS_PREVIOUS_COMMIT")


class BranchNode(Model):
    __primarykey__ = "name"

    name = Property()
    commit = RelatedTo("CommitNode", "TRACKS_COMMIT")
