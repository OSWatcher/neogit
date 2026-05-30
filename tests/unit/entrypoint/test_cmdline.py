"""Unit tests for the CLI argument routing in neogit.entrypoint.cmdline."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from neogit.entrypoint import cmdline
from neogit.model import DiffStatus, FSDiffObject


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


def test_diff_prints_file_lines_and_skips_dirs(patched_cmdline, monkeypatch, capsys):
    patched_cmdline.diff.return_value = [
        FSDiffObject(DiffStatus.MOD, True, Path("/fs/nls"), "o", "n"),
        FSDiffObject(DiffStatus.MOD, False, Path("/fs/nls/Kconfig"), "o", "n"),
        FSDiffObject(DiffStatus.NEW, False, Path("/fs/new.c"), None, "n"),
    ]
    monkeypatch.setattr(sys, "argv", ["neogit", "diff", "aaa", "bbb"])

    cmdline.handle_cmdline()

    patched_cmdline.diff.assert_called_once_with("aaa", "bbb")
    out = capsys.readouterr().out
    # Directory entry suppressed; only the two files appear, status-first.
    assert "/fs/nls\n" not in out
    assert "M  /fs/nls/Kconfig" in out
    assert "A  /fs/new.c" in out
