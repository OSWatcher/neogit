from pathlib import Path

import pytest
from py2neo.ogm import Repository

from neogit.service import Neogit
from tests.conftest import Neo4jConnection


@pytest.mark.dev
def test_py2neo_connection(neo4j_con: Neo4jConnection):
    repo = Repository(neo4j_con.to_bolt(crendentials=True))  # noqa: F841
    raise AssertionError()


@pytest.mark.dev
def test_commit_dir(py2neo_repo):
    path = Path("")
    neogit = Neogit(path, py2neo_repo)

    neogit.commit("first commit")
    raise AssertionError()


@pytest.mark.dev
def test_persistent(persistent_neo4j_db, persistent_minio_db):
    raise AssertionError()
