# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""Human-friendly rendering of a branch's commit log for the CLI.

Builds a Rich ``Tree`` rooted at the branch name with one leaf per commit,
each ``<full-sha1>  <name>``, newest-first. Returning a ``Tree`` (not a string)
lets the CLI own the ``rich.console.Console``: color shows on a TTY and is
stripped to plain text when piped. Branch and commit names are escaped so
bracket characters are not parsed as Rich markup tags.
"""

from typing import List

from rich.markup import escape
from rich.tree import Tree

from neogit.model.neo import Commit


def render_log_tree(branch_name: str, commits: List[Commit]) -> Tree:
    """Return a Rich Tree: branch name root, one ``<sha1>  <name>`` leaf per commit."""
    tree = Tree(f"[bold]{escape(branch_name)}[/]")
    for commit in commits:
        tree.add(f"[yellow]{commit.hash}[/]  {escape(commit.name)}")
    return tree
