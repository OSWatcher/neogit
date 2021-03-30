"""Neogit

Usage:
  neogit [options] commit <name>

Options:
  -h --help             Show this screen.
  --version             Show version.
  -r ROOT --root=ROOT   Specify repo root directory
"""
from docopt import docopt
from neogit.service import Neogit
from pathlib import Path
from neogit.repo import Py2NeoRepository


def handle_cmdline():
    args = docopt(__doc__)
    # handle root
    root_repo: Path = Path.cwd()
    if args["--root"]:
        root_repo = Path(args["--root"])
    repo = Py2NeoRepository()
    git = Neogit(root_repo, repo)
    if args["commit"]:
        commit_name = args["<name>"]
        git.commit(commit_name)
