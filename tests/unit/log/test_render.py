# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

import io
from dataclasses import dataclass

from rich.console import Console

from neogit.log.render import render_log_tree


@dataclass
class FakeCommit:
    """Stand-in for a neomodel Commit: render_log_tree only reads .hash/.name."""

    hash: str
    name: str


def _render_plain(branch_name, commits) -> str:
    """Render the tree through a non-TTY Console so styling is stripped to plain text."""
    buffer = io.StringIO()
    Console(file=buffer).print(render_log_tree(branch_name, commits))
    return buffer.getvalue()


def test_root_is_branch_name_and_leaves_are_hash_then_name():
    commits = [
        FakeCommit("a" * 40, "newest"),
        FakeCommit("b" * 40, "oldest"),
    ]
    out = _render_plain("master", commits)
    assert "master" in out
    # Full 40-char hash followed by the commit name, newest-first.
    assert ("a" * 40) + "  newest" in out
    assert ("b" * 40) + "  oldest" in out
    assert out.index("newest") < out.index("oldest")


def test_empty_commit_list_renders_only_root():
    out = _render_plain("master", [])
    assert "master" in out
    assert "  " not in out.replace("master", "")  # no commit leaves


def test_brackets_in_names_are_escaped():
    # Names that look like Rich markup tags ('[red]', '[bold]') must be escaped
    # so they appear literally rather than being consumed as styling.
    out = _render_plain("[red]danger", [FakeCommit("c" * 40, "[bold]snap")])
    assert "[red]danger" in out
    assert "[bold]snap" in out
