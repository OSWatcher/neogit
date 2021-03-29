from py2neo.ogm import Model, Property, RelatedTo


class Blob(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()


class Tree(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()
    children_blobs = RelatedTo("Blob", "HAS_CHILD_BLOB")
    children_trees = RelatedTo("Tree", "HAS_CHILD_TREE")


class Commit(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()
    name = Property()
    filesystem = RelatedTo("Tree", "HAS_FILESYSTEM")
    previous_commit = RelatedTo("Commit", "HAS_PREVIOUS_COMMIT")


class Branch(Model):
    __primarykey__ = "name"

    name = Property()
    commit = RelatedTo("Commit", "TRACKS_COMMIT")
