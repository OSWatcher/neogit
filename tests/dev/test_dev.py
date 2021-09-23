import pytest


@pytest.mark.dev
def test_persistent(persistent_neo4j_db, persistent_minio_db):
    raise AssertionError()
