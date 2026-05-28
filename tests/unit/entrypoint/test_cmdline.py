"""Unit tests for the CLI argument routing in neogit.entrypoint.cmdline."""
import sys
from unittest.mock import MagicMock

import pytest

from neogit.entrypoint import cmdline


@pytest.fixture
def patched_cmdline(monkeypatch):
    """Patch out object storage and the Neogit service so handle_cmdline can run
    without a real Neo4j/object-storage backend. Returns the Neogit mock instance."""
    monkeypatch.setattr(cmdline, "ObjectConfig", MagicMock())
    monkeypatch.setattr(cmdline, "TSObjectStorage", MagicMock())
    neogit_cls = MagicMock()
    monkeypatch.setattr(cmdline, "Neogit", neogit_cls)
    return neogit_cls.return_value


def test_commit_branch_arg_is_forwarded_as_branch_name(patched_cmdline, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["neogit", "commit", "snap-1", "branch", "feature", "--root", "/tmp"])

    cmdline.handle_cmdline()

    _, kwargs = patched_cmdline.commit.call_args
    assert kwargs.get("branch_name") == "feature"


def test_commit_without_branch_passes_none_branch_name(patched_cmdline, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["neogit", "commit", "snap-1", "--root", "/tmp"])

    cmdline.handle_cmdline()

    _, kwargs = patched_cmdline.commit.call_args
    assert kwargs.get("branch_name") is None
