"""Neogit

Usage:
  neogit [options] init
  neogit [options] commit <name> [branch <branch>] [--unique] [--before=<commit>]
  neogit [options] branch <name> <commit>
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
from importlib.metadata import version
from pathlib import Path

from docopt import docopt

from neogit.config import ObjectConfig, settings
from neogit.object_storage import LibcloudObjectStorage, TSObjectStorage
from neogit.service import Neogit
from neogit.utils import setup_logging


def post_mortem(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            logging.exception("Post Mortem: An unhandled exception occurred.")
            import sys

            import ipdb  # type: ignore

            _, _, tb = sys.exc_info()
            ipdb.post_mortem(tb)

    return wrapper


@post_mortem
def handle_cmdline():
    args = docopt(__doc__, version=f"neogit {version('neogit')}")
    # handle root
    root_repo: Path = Path.cwd()
    if args["--root"]:
        root_repo = Path(args["--root"])
    gui_enabled = args["--gui"]
    setup_logging(args["--debug"], basic_config=True)
    # init TSObjectStorage and inject dependency
    obj_config = ObjectConfig.from_settings(settings)
    tsobj = TSObjectStorage(LibcloudObjectStorage, obj_config)
    git = Neogit(tsobj, gui_enabled, args["--debug"])
    if args["init"]:
        return git.init()
    if args["commit"]:
        commit_name = args["<name>"]
        branch_name = args["<branch>"]
        unique = args.get("--unique", False)
        before = args.get("--before", None)
        return git.commit(commit_name, root_repo, branch_name=branch_name, unique=unique, before=before)
    if args["branch"]:
        branch_name = args["<name>"]
        commit_hash = args["<commit>"]
        return git.create_branch(branch_name, commit_hash)
    if args["diff"]:
        ref1 = args["<ref1>"]
        ref2 = args["<ref2>"]
        for diff_obj in git.diff(ref1, ref2):
            print(diff_obj)
        return
