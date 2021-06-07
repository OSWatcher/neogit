from pathlib import Path

from neogit.service import Neogit


def test_git_log(neo4j_con, fakefs_one_empty_file):
    neogit = Neogit(Path("/"))
    neogit.init()
    neogit.commit("first_commit")
