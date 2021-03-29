"""Test the Repository Pattern"""
from typing import Tuple

from neo4j import BoltDriver
from py2neo.ogm import Model, Property

from neogit.repo.py2neo import Py2NeoRepository


class Branch(Model):
    name = Property()


def test_save(driver_con: Tuple[Py2NeoRepository, BoltDriver]):
    repo, driver = driver_con
    master = Branch()
    branch_name = "master"
    master.name = branch_name

    repo.save(master)

    with driver.session() as s:
        cursor = s.run(f"MATCH (b:Branch {{name: '{branch_name}'}}) RETURN b")
        res = list(cursor)
        assert branch_name, res[0]["b"]["name"]
        assert 1 == len(res)
