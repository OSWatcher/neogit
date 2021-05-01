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

from logging.config import dictConfig
from pathlib import Path

import yaml
from docopt import docopt

from neogit.service import Neogit


def setup_logging(debug_enabled: bool):
    log_config_path = Path(__file__).parent.parent / "logging.yaml"
    with open(log_config_path) as f:
        config = yaml.safe_load(f)

    dictConfig(config)


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
