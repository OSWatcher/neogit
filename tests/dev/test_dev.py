import pytest
from py2neo.ogm import Repository

from tests.conftest import Neo4jConnection


@pytest.mark.dev
def test_py2neo_connection(neo4j_con: Neo4jConnection):
    repo = Repository(neo4j_con.to_bolt(crendentials=True))  # noqa: F841
    raise AssertionError()
