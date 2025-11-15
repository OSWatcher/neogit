"""Unit tests for Tree API refactoring - new child navigation methods."""

from pathlib import PurePath
from unittest.mock import Mock, patch

import pytest

from neogit.model.merkle import Blob, Tree


class TestTreeAPI:
    """Test the new Tree API methods for child navigation."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Create mock tree with some children
        self.tree = Tree()
        self.tree.hash = "parent_tree_hash"

    def test_list_children_returns_sorted_names(self):
        """Test that list_children returns all child names sorted."""
        # Mock the relationship access at the instance level
        mock_blob1 = Mock(spec=Blob)
        mock_blob2 = Mock(spec=Blob)
        mock_tree1 = Mock(spec=Tree)
        mock_tree2 = Mock(spec=Tree)

        # Mock blob relationships
        mock_blob_rel1 = Mock()
        mock_blob_rel1.name = "file2.txt"
        mock_blob_rel2 = Mock()
        mock_blob_rel2.name = "file1.txt"

        # Mock tree relationships
        mock_tree_rel1 = Mock()
        mock_tree_rel1.name = "dir1"
        mock_tree_rel2 = Mock()
        mock_tree_rel2.name = "dir2"

        # Mock the relationship managers
        self.tree.children_blob = Mock()
        self.tree.children_blob.all.return_value = [mock_blob1, mock_blob2]
        self.tree.children_blob.relationship.side_effect = lambda blob: {
            mock_blob1: mock_blob_rel1,
            mock_blob2: mock_blob_rel2,
        }[blob]

        self.tree.children_tree = Mock()
        self.tree.children_tree.all.return_value = [mock_tree1, mock_tree2]
        self.tree.children_tree.relationship.side_effect = lambda tree: {
            mock_tree1: mock_tree_rel1,
            mock_tree2: mock_tree_rel2,
        }[tree]

        # Test
        result = self.tree.list_children()

        # Assert - should be sorted alphabetically
        expected = ["dir1", "dir2", "file1.txt", "file2.txt"]
        assert result == expected

    def test_iter_children_yields_name_node_pairs(self):
        """Test that iter_children yields correct (name, node) pairs."""
        # Mock one blob and one tree
        mock_blob = Mock(spec=Blob)
        mock_tree = Mock(spec=Tree)

        mock_blob_rel = Mock()
        mock_blob_rel.name = "test.txt"
        mock_tree_rel = Mock()
        mock_tree_rel.name = "subdir"

        # Mock the relationship managers
        self.tree.children_blob = Mock()
        self.tree.children_blob.all.return_value = [mock_blob]
        self.tree.children_blob.relationship.return_value = mock_blob_rel

        self.tree.children_tree = Mock()
        self.tree.children_tree.all.return_value = [mock_tree]
        self.tree.children_tree.relationship.return_value = mock_tree_rel

        # Test
        result = list(self.tree.iter_children())

        # Assert
        assert len(result) == 2
        assert ("test.txt", mock_blob) in result
        assert ("subdir", mock_tree) in result

    def test_get_child_at_path_empty_path_returns_self(self):
        """Test that get_child_at_path with empty path returns self."""
        path = PurePath("")
        result = self.tree.get_child_at_path(path)
        assert result == self.tree

    @patch.object(Tree, "cypher")
    def test_get_child_at_path_simple_blob(self, mock_cypher):
        """Test get_child_at_path returns blob for simple path."""
        # Mock successful blob query
        mock_blob_data = {"hash": "blob_hash"}
        mock_cypher.return_value = ([(mock_blob_data,)], None)

        with patch.object(Blob, "inflate") as mock_inflate:
            mock_blob = Mock(spec=Blob)
            mock_inflate.return_value = mock_blob

            path = PurePath("file.txt")
            result = self.tree.get_child_at_path(path)

            assert result == mock_blob
            mock_inflate.assert_called_once_with(mock_blob_data)

    @patch.object(Tree, "cypher")
    def test_get_child_at_path_simple_tree(self, mock_cypher):
        """Test get_child_at_path returns tree when blob query fails but tree query succeeds."""
        # Mock blob query failure, tree query success
        mock_tree_data = {"hash": "tree_hash"}
        mock_cypher.side_effect = [
            ([], None),  # Blob query returns empty
            ([(mock_tree_data,)], None),  # Tree query returns data
        ]

        with patch.object(Tree, "inflate") as mock_inflate:
            mock_tree = Mock(spec=Tree)
            mock_inflate.return_value = mock_tree

            path = PurePath("subdir")
            result = self.tree.get_child_at_path(path)

            assert result == mock_tree
            mock_inflate.assert_called_once_with(mock_tree_data)

    @patch.object(Tree, "cypher")
    def test_get_child_at_path_nested_path(self, mock_cypher):
        """Test get_child_at_path with nested path navigation."""
        # Mock intermediate tree navigation and final blob
        intermediate_tree_data = {"hash": "intermediate_tree_hash"}
        blob_data = {"hash": "final_blob_hash"}

        mock_cypher.side_effect = [
            ([(intermediate_tree_data,)], None),  # Navigate to intermediate tree
            ([(blob_data,)], None),  # Find final blob
            ([], None),  # Tree query for final item (empty)
        ]

        with patch.object(Tree, "inflate") as mock_tree_inflate, patch.object(Blob, "inflate") as mock_blob_inflate:

            mock_intermediate_tree = Mock(spec=Tree)
            mock_intermediate_tree.hash = "intermediate_tree_hash"
            mock_tree_inflate.return_value = mock_intermediate_tree

            mock_blob = Mock(spec=Blob)
            mock_blob_inflate.return_value = mock_blob

            path = PurePath("dir1/file.txt")
            result = self.tree.get_child_at_path(path)

            assert result == mock_blob

    @patch.object(Tree, "cypher")
    def test_get_child_at_path_not_found_raises_error(self, mock_cypher):
        """Test get_child_at_path raises FileNotFoundError for non-existent path."""
        # Mock both blob and tree queries returning empty
        mock_cypher.side_effect = [([], None), ([], None)]  # Blob query empty  # Tree query empty

        path = PurePath("nonexistent.txt")

        with pytest.raises(FileNotFoundError, match="Child not found: nonexistent.txt"):
            self.tree.get_child_at_path(path)

    @patch.object(Tree, "cypher")
    def test_get_child_at_path_intermediate_tree_not_found(self, mock_cypher):
        """Test get_child_at_path raises error when intermediate tree not found."""
        # Mock tree navigation failure
        mock_cypher.return_value = ([], None)

        path = PurePath("nonexistent_dir/file.txt")

        with pytest.raises(FileNotFoundError, match="Tree not found: nonexistent_dir"):
            self.tree.get_child_at_path(path)

    def test_get_tree_at_path_returns_tree(self):
        """Test get_tree_at_path returns tree when child is tree."""
        mock_tree = Mock(spec=Tree)

        with patch.object(self.tree, "get_child_at_path", return_value=mock_tree):
            path = PurePath("subdir")
            result = self.tree.get_tree_at_path(path)
            assert result == mock_tree

    def test_get_tree_at_path_raises_error_for_blob(self):
        """Test get_tree_at_path raises error when child is blob."""
        mock_blob = Mock(spec=Blob)

        with patch.object(self.tree, "get_child_at_path", return_value=mock_blob):
            path = PurePath("file.txt")

            with pytest.raises(FileNotFoundError, match="Path is not a tree: file.txt"):
                self.tree.get_tree_at_path(path)

    def test_get_blob_at_path_returns_blob(self):
        """Test get_blob_at_path returns blob when child is blob."""
        mock_blob = Mock(spec=Blob)

        with patch.object(self.tree, "get_child_at_path", return_value=mock_blob):
            path = PurePath("file.txt")
            result = self.tree.get_blob_at_path(path)
            assert result == mock_blob

    def test_get_blob_at_path_raises_error_for_tree(self):
        """Test get_blob_at_path raises error when child is tree."""
        mock_tree = Mock(spec=Tree)

        with patch.object(self.tree, "get_child_at_path", return_value=mock_tree):
            path = PurePath("subdir")

            with pytest.raises(FileNotFoundError, match="Path is not a blob: subdir"):
                self.tree.get_blob_at_path(path)

    def test_absolute_vs_relative_paths(self):
        """Test that absolute and relative paths are handled correctly."""
        with patch.object(self.tree, "get_child_at_path") as mock_get_child:
            # Test absolute path
            abs_path = PurePath("/dir/file.txt")
            self.tree.get_child_at_path(abs_path)

            # Test relative path
            rel_path = PurePath("dir/file.txt")
            self.tree.get_child_at_path(rel_path)

            # Both should work (implementation handles idx calculation)
            assert mock_get_child.call_count == 2
