# from neogit.merkle.utils import merkelize_dir, merkelize_file
# from neogit.model import Blob, Tree
# from tests.conftest import TEST_DATA, TEST_DATA_FS
#
# TEST_DATA_SHA = TEST_DATA / "sha1"
#
#
# def test_merkelize_file():
#     filepath = TEST_DATA_SHA / "64k.raw"
#     blob: Blob = merkelize_file(filepath)
#     assert "0fb500a2b6ff43385ea59a7d4d7ca7ad78797a67" == blob.sha1sum
#
#
# def test_merkelize_dir_empty():
#     root = TEST_DATA_FS / "dir_empty"
#     expected_tree = Tree()
#     expected_tree.sha1sum = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
#     tree_fs = {}
#
#     tree: Tree = merkelize_dir(root, tree_fs)
#
#     assert expected_tree == tree
#
#
# def test_merkelize_dir_one_file():
#     root = TEST_DATA_FS / "dir_one_file"
#     tree_fs = {}
#     expected_tree = Tree()
#     expected_tree.sha1sum = "0032782e6f3381866532878f1bd3c1405203fff7"
#     expected_child = Blob()
#     expected_child.sha1sum = "4c4e3587ef717dff0d533394483cd5d5feaa983a"
#     expected_tree.children_blob["file.raw"] = expected_child
#
#     tree: Tree = merkelize_dir(root, tree_fs)
#
#     assert expected_tree == tree
#
#
# def test_merkelize_dir_multiple_files():
#     root = TEST_DATA_FS / "dir_multiple_files"
#     tree_fs = {}
#     expected_tree = Tree()
#     expected_tree.sha1sum = "286f4a2c4f99c90021424bd3a7b11d341c302985"
#     expected_child_file1 = Blob()
#     expected_child_file1.sha1sum = "b1b609377a75bde0f7bf4b176af625680b50baaf"
#     expected_child_file2 = Blob()
#     expected_child_file2.sha1sum = "69e6b4938a461897eebaaf6484bdd29f4c125332"
#     expected_child_file3 = Blob()
#     expected_child_file3.sha1sum = "b2147e8e177f0a53daea590d04b944f8dd656cce"
#     expected_tree.children_blob["file1.raw"] = expected_child_file1
#     expected_tree.children_blob["file2.raw"] = expected_child_file2
#     expected_tree.children_blob["file3.raw"] = expected_child_file3
#
#     tree: Tree = merkelize_dir(root, tree_fs)
#
#     assert expected_tree == tree
#
#
# def test_merkelize_dir_one_subdir():
#     root = TEST_DATA_FS / "dir_one_subdir"
#     subdir_tree = Tree()
#     subdir_tree.sha1sum = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
#     tree_fs = {root / "subdir": subdir_tree}
#     expected_tree = Tree()
#     expected_tree.sha1sum = "ac7b58cb43a320c493188b1a976a27f94a4e53ea"
#     expected_tree.children_tree["subdir"] = subdir_tree
#
#     tree: Tree = merkelize_dir(root, tree_fs)
#
#     assert expected_tree == tree
#
#
# def test_merkelize_dir_multiple_subdirs():
#     root = TEST_DATA_FS / "dir_multiple_subdirs"
#     empty_dir_sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
#     subdir_tree = Tree()
#     subdir_tree.sha1sum = empty_dir_sha1
#     tree_fs = {root / "subdir1": subdir_tree, root / "subdir2": subdir_tree, root / "subdir3": subdir_tree}
#     expected_tree = Tree()
#     expected_tree.sha1sum = "0dc6fc1493c0c6a9d56007b436ac6a3613e5e346"
#     expected_tree.children_tree["subdir1"] = subdir_tree
#     expected_tree.children_tree["subdir2"] = subdir_tree
#     expected_tree.children_tree["subdir3"] = subdir_tree
#
#     tree: Tree = merkelize_dir(root, tree_fs)
#
#     assert expected_tree == tree
