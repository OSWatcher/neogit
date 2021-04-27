"""Neogit

Usage:
  neogit [options] init
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

from neogit.service import Neogit


def setup_logging(debug_enabled: bool):
    log_lvl = logging.INFO
    if debug_enabled:
        log_lvl = logging.DEBUG
    logging.basicConfig(level=log_lvl)
    # silence neo4j
    logging.getLogger("neo4j").setLevel(logging.WARNING)


def handle_cmdline():
    args = docopt(__doc__)
    setup_logging(args["--debug"])
    # handle root
    root_repo: Path = Path.cwd()
    if args["--root"]:
        root_repo = Path(args["--root"])
    git = Neogit(root_repo)
    if args["init"]:
        git.init()
    if args["commit"]:
        commit_name = args["<name>"]
        git.commit(commit_name)
