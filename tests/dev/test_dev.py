import pytest


@pytest.mark.dev
def test_persistent(clean_neo4j_db, clean_minio_db):
    raise AssertionError()
