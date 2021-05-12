"""pytest configuration and fixtures"""

import logging
import random
import string
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Optional, Tuple
from urllib.error import URLError
from urllib.request import urlopen

from neo4j import BoltDriver, GraphDatabase
from pytest import fixture

from neogit.config import ObjectConfig
from neogit.object_storage import FakeObjectStorage, LibcloudObjectStorage, TSObjectStorage
from neogit.repo.py2neo import Py2NeoRepository

NEO4J_VERSION = "4.2.4"
DEFAULT_USERNAME = "neo4j"
DEFAULT_PASSWORD = "admin"
TEST_DATA = Path(__file__).parent / "data"
TEST_DATA_FS = TEST_DATA / "fs"
ROOT_REPO = Path(__file__).parent.parent



@dataclass
class Neo4jConnection:
    protocol: str
    hostname: str
    bolt_port: int
    http_port: int
    username: str
    password: str
    driver: Optional[BoltDriver]

    def to_http(self):
        return f"http://{self.hostname}:{self.http_port}"

    def to_bolt(self, crendentials=False):
        if crendentials:
            return f"bolt://{self.username}:{self.password}@{self.hostname}:{self.bolt_port}"
        else:
            return f"bolt://{self.hostname}:{self.bolt_port}"


@fixture(scope="session")
def random_name():
    length = 8
    return "".join(random.choices(string.ascii_lowercase, k=length))


@fixture(scope="session")
def start_neo4j_db(random_name: str):
    """start a neo4j db using Docker"""
    cmdline = [
        "docker",
        "run",
        "--detach",
        "--publish=7474:7474",
        "--publish=7687:7687",
        "--env",
        "NEO4J_AUTH=none",
        f"--name={random_name}",
        f"neo4j:{NEO4J_VERSION}",
    ]
    subprocess.check_call(cmdline)
    con = Neo4jConnection(
        protocol="bolt",
        hostname="localhost",
        bolt_port=7687,
        http_port=7474,
        username=DEFAULT_USERNAME,
        password=DEFAULT_PASSWORD,
        driver=None,
    )
    yield random_name, con
    cmdline = ["docker", "rm", "--force", random_name]
    subprocess.check_call(cmdline)


@fixture(scope="session")
def neo4j_ready(start_neo4j_db: Tuple[str, Neo4jConnection]):
    """ensure neo4jdb is ready"""
    container_name, con = start_neo4j_db
    opened = False
    while not opened:
        try:
            logging.info("attempting to connect to DB %s", con.to_http())
            with urlopen(con.to_http(), timeout=1) as opened_url:
                opened_url.read()
        except (URLError, ConnectionError):
            time.sleep(0.7)
        else:
            opened = True
    yield con


@fixture(scope="function")
def driver_con(neo4j_con: Neo4jConnection):
    repo = Py2NeoRepository(neo4j_con.to_bolt(crendentials=True))
    neo_drv = neo4j_con.driver
    yield repo, neo_drv
    s = neo_drv.session()
    s.run("MATCH (n) DETACH DELETE n")


@fixture(scope="function")
def py2neo_repo(driver_con):
    repo, neo4j_drv = driver_con
    yield repo


@fixture(scope="session")
def neo4j_con(neo4j_ready: Neo4jConnection):
    con = neo4j_ready
    # start db connection with the most basic driver
    creds = (con.username, con.password)
    con.driver = GraphDatabase.driver(con.to_bolt(crendentials=False), auth=creds)
    yield con


# object storage fixtures


@fixture(
    params=[
        {"cls": FakeObjectStorage, "config": None},
        {"cls": LibcloudObjectStorage, "config": ObjectConfig(provider="local", key="to_change")},
    ],
    ids=("Fake", "Libcloud"),
)
def init_object_storage(tmp_path, request):
    param = request.param
    cls = param["cls"]
    config = param["config"]
    if cls == LibcloudObjectStorage:
        config.key = str(tmp_path)
    ts_object = TSObjectStorage(cls, config)
    yield from container_ctx_and_yield(ts_object)


@fixture
def init_fake_object_storage():
    ts_object = TSObjectStorage(FakeObjectStorage, None)
    yield from container_ctx_and_yield(ts_object)


@fixture(scope="function")
def init_libcloud_object_storage_per_func():
    with TemporaryDirectory() as tmp_path:
        yield from init_libcloud(tmp_path)


@fixture(scope="module")
def init_libcloud_object_storage_per_module():
    with TemporaryDirectory() as tmp_path:
        yield from init_libcloud(tmp_path)


def init_libcloud(tmppath):
    config = ObjectConfig(provider="local", key=str(tmppath))
    ts_object = TSObjectStorage(LibcloudObjectStorage, config)
    yield from container_ctx_and_yield(ts_object)


def container_ctx_and_yield(ts_object) -> Iterator[TSObjectStorage]:
    driver = ts_object.instance
    driver.create_container("objects")
    yield ts_object
    # cleanup
    for cont in driver.iterate_containers():
        driver.delete_container(cont)
