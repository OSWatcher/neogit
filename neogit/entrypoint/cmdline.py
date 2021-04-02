"""Neogit

Usage:
  neogit [options] commit <name>

Options:
  -h --help             Show this screen.
  --version             Show version.
  -r ROOT --root=ROOT   Specify repo root directory
  -d --debug            Toogle debug output
"""

import logging
from pathlib import Path

from docopt import docopt

from neogit.repo import Py2NeoRepository
from neogit.service import Neogit


def handle_cmdline():
    args = docopt(__doc__)
    log_lvl = logging.INFO
    if args["--debug"]:
        log_lvl = logging.DEBUG
    logging.basicConfig(level=log_lvl)
    # silence py2neo
    logging.getLogger("py2neo.client").setLevel(logging.WARNING)
    # handle root
    root_repo: Path = Path.cwd()
    if args["--root"]:
        root_repo = Path(args["--root"])
    repo = Py2NeoRepository()
    git = Neogit(root_repo, repo)
    if args["commit"]:
        commit_name = args["<name>"]
        git.commit(commit_name)
