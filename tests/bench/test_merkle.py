from pathlib import Path

from more_itertools import consume

from neogit.merkle import MerkleFSTree


def test_merkle_first(tmp_path, init_libcloud_object_storage_per_module, arg_repo_root):
    """merklize a repository"""
    assert arg_repo_root
    ts_object = init_libcloud_object_storage_per_module
    repo = Path(arg_repo_root)
    builder = MerkleFSTree(repo, ts_object)
    consume(builder.merkelize())


def test_merkle_second(tmp_path, init_libcloud_object_storage_per_module, arg_repo_root):
    """merklize a repository again, but with the same object storage, so objects are already indexed"""
    assert arg_repo_root
    ts_object = init_libcloud_object_storage_per_module
    repo = Path(arg_repo_root)
    builder = MerkleFSTree(repo, ts_object)
    consume(builder.merkelize())
