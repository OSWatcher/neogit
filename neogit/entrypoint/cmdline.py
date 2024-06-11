"""Neogit

Usage:
  neogit [options] init
  neogit [options] commit <name>
  neogit [options] diff <ref1> <ref2>

Options:
  -h --help             Show this screen.
  --version             Show version.
  -r ROOT --root=ROOT   Specify repo root directory
  -g --gui              Toggle the console interface
  -d --debug            Toogle debug output
"""

import logging
from functools import wraps
from pathlib import Path

from docopt import docopt

from neogit.config import ObjectConfig, settings
from neogit.object_storage import LibcloudObjectStorage, TSObjectStorage
from neogit.service import Neogit


def post_mortem(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            logging.exception("Post Mortem: An unhandled exception occurred.")
            import sys

            import ipdb

            _, _, tb = sys.exc_info()
            ipdb.post_mortem(tb)

    return wrapper


@post_mortem
def handle_cmdline():
    args = docopt(__doc__)
    # handle root
    root_repo: Path = Path.cwd()
    if args["--root"]:
        root_repo = Path(args["--root"])
    gui_enabled = args["--gui"]
    # init TSObjectStorage and inject dependency
    obj_config = ObjectConfig.from_settings(settings)
    tsobj = TSObjectStorage(LibcloudObjectStorage, obj_config)
    git = Neogit(tsobj, gui_enabled, args["--debug"])
    if args["init"]:
        git.init()
    if args["commit"]:
        commit_name = args["<name>"]
        git.commit(commit_name, root_repo)
    if args["diff"]:
        ref1 = args["<ref1>"]
        ref2 = args["<ref2>"]
        for diff_obj in git.diff(ref1, ref2):
            print(diff_obj)
