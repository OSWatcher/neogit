from neomodel import RelationshipTo, StringProperty, StructuredNode, StructuredRel


class HasChildRel(StructuredRel):
    """HAS_CHILD relationship"""

    """filename"""
    name = StringProperty(required=True)


class BaseMerkleNode(StructuredNode):
    """A simple abstract class to put common properties between Blobs and Trees"""

    __abstract_node__ = True
    hash = StringProperty(unique_index=True, required=True)


class Blob(BaseMerkleNode):
    pass


class Tree(BaseMerkleNode):
    hash = StringProperty(unique_index=True, required=True)
    children_blob = RelationshipTo(Blob, "HAS_CHILD", model=HasChildRel)
    children_tree = RelationshipTo("Tree", "HAS_CHILD", model=HasChildRel)
