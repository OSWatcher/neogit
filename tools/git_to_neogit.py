#!/usr/bin/env python3

import logging
import subprocess
import tarfile
from itertools import islice
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import coloredlogs
from docopt import docopt
from git import Repo

"""Git to Neogit

Usage:
    git_to_neogit [options] <git_repo>

Options:
  -h --help             Show this screen.
  --limit=<lm>          Limit
  --version             Show version.
  -d --debug            Toogle debug output
"""

LOG_FMT = "%(asctime)s:%(name)s:%(levelname)s:%(message)s"


def setup_logging(debug_enabled: bool):
    level = logging.INFO
    if debug_enabled:
        level = logging.DEBUG
    logging.basicConfig(level=level)
    coloredlogs.install(level=level, fmt=LOG_FMT)


def handle_cmdline():
    args = docopt(__doc__)
    setup_logging(args["--debug"])
    git_repo_path = Path(args["<git_repo>"])
    if not git_repo_path.exists():
        raise RuntimeError("git repo does not exists")
    limit = args["--limit"]
    if limit:
        limit = int(args["--limit"])

    git_repo = Repo(git_repo_path)
    for index, commit in enumerate(islice(reversed(list(git_repo.iter_commits())), limit)):
        logging.info("[%s/%s] Commit: %s - %s", index + 1, limit, commit.hexsha, commit.message)
        with TemporaryDirectory(prefix="git_to_neogit_extract") as tmp_extract:
            with NamedTemporaryFile(prefix="git_to_neogit_archive") as tmparchive:
                logging.info("Archive: %s", tmparchive.name)
                git_repo.archive(tmparchive, format="tar", treeish=commit.hexsha)
                tmparchive.flush()
                # extract
                logging.info("Extract: %s", tmp_extract)
                with tarfile.TarFile(tmparchive.name) as tarball:
                    tarball.extractall(tmp_extract)
            logging.info("Capture with Neogit")
            subprocess.check_call(["python", "-m", "neogit", "commit", commit.message, "-r", tmp_extract])


def main():
    handle_cmdline()


if __name__ == "__main__":
    main()
