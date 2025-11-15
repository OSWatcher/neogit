"""Integration tests for Tree API methods with real Neo4j data."""

from pathlib import PurePath

import pytest

from neogit.model.neo import Commit
from tests.data.fs.conftest import TEST_DATA_FS


class TestTreeAPIIntegration:
    """Integration tests for Tree API methods using real Neo4j data."""

    def test_new_tree_api_methods_with_real_data(self, neogit_init):
        """Test new Tree API methods work with real filesystem data."""
        neogit = neogit_init
        commit_name = "test_tree_api_commit"

        # Create a commit with test filesystem
        neogit.commit(commit_name, TEST_DATA_FS.dir_one_file.path)

        # Get the committed tree
        commit = Commit.nodes.get(name=commit_name)
        tree = commit.filesystem[0]

        # Test list_children
        children = tree.list_children()
        assert isinstance(children, list)
        assert "file.raw" in children  # From TEST_DATA_FS.dir_one_file
        assert children == sorted(children)  # Should be sorted

        # Test iter_children
        child_items = list(tree.iter_children())
        assert len(child_items) > 0

        # Each item should be (name, node) tuple
        for name, node in child_items:
            assert isinstance(name, str)
            assert hasattr(node, "hash")  # Should be Tree or Blob

        # Test get_child_at_path for file
        blob = tree.get_child_at_path(PurePath("file.raw"))
        assert blob is not None
        assert hasattr(blob, "hash")

        # Test get_blob_at_path
        blob2 = tree.get_blob_at_path(PurePath("file.raw"))
        assert blob2.hash == blob.hash

        # Test get_tree_at_path should fail for blob
        with pytest.raises(FileNotFoundError, match="Path is not a tree"):
            tree.get_tree_at_path(PurePath("file.raw"))

        # Test non-existent path
        with pytest.raises(FileNotFoundError):
            tree.get_child_at_path(PurePath("nonexistent.file"))

    def test_tree_api_backwards_compatibility(self, neogit_init):
        """Test that existing get_blob_at_path still works as before."""
        neogit = neogit_init
        commit_name = "test_backwards_compatibility"

        # Create a commit
        neogit.commit(commit_name, TEST_DATA_FS.dir_one_file.path)

        # Get the committed tree
        commit = Commit.nodes.get(name=commit_name)
        tree = commit.filesystem[0]

        # Test the original get_blob_at_path still works
        blob = tree.get_blob_at_path(PurePath("file.raw"))
        assert blob is not None
        assert hasattr(blob, "hash")

        # Should work exactly as before
        expected_hash = "4c4e3587ef717dff0d533394483cd5d5feaa983a"  # From test data
        assert blob.hash == expected_hash
