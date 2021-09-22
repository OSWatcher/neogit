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

from neogit.config import ObjectConfig, settings
from neogit.object_storage import FakeObjectStorage, LibcloudObjectStorage, TSObjectStorage
from neogit.repo.py2neo import Py2NeoRepository

NEO4J_VERSION = "4.2.4"
MINIO_VERSION = "RELEASE.2021-05-11T23-27-41Z"
DEFAULT_USERNAME = "neo4j"
DEFAULT_PASSWORD = "admin"
TEST_DATA = Path(__file__).parent / "data"
TEST_DATA_FS = TEST_DATA / "fs"
ROOT_REPO = Path(__file__).parent.parent


def pytest_addoption(parser):
    """add a new option to pass a specific directory to be merkelized"""
    parser.addoption("--repo", action="store", help="root directory to be indexed")


@fixture
def arg_repo_root(pytestconfig):
    return pytestconfig.getoption("repo")


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


def random_name():
    length = 8
    return "".join(random.choices(string.ascii_lowercase, k=length))


@fixture(scope="session")
def start_neo4j_db():
    """start a neo4j db using Docker"""
    cont_name = random_name()
    cmdline = [
        "docker",
        "run",
        "--detach",
        "--publish=7474:7474",
        "--publish=7687:7687",
        "--env",
        "NEO4J_AUTH=none",
        "--env",
        'NEO4JLABS_PLUGINS=["apoc"]',
        f"--name={cont_name}",
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
    yield cont_name, con
    cmdline = ["docker", "rm", "--force", cont_name]
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


# Minio object storage


@fixture(scope="session")
def minio_db():
    """start a MinIO db using Docker"""
    cont_name = random_name()
    provider = "minio"
    key = "minioadmin"
    secret = "minioadmin"
    port = 9000
    host = "127.0.0.1"
    secure = False
    cmdline = [
        "docker",
        "run",
        "--detach",
        f"--publish=9000:{port}",
        f"--name={cont_name}",
        f"minio/minio:{MINIO_VERSION}",
        "server",
        "/data",
    ]
    subprocess.check_call(cmdline)
    # update settings
    settings.object.provider = provider
    settings.object.key = key
    settings.object.secret = secret
    settings.object.host = host
    settings.object.port = port
    settings.object.secure = secure
    # ensure ready to receive connections
    time.sleep(2)
    yield
    cmdline = ["docker", "rm", "--force", cont_name]
    subprocess.check_call(cmdline)


# fake filesystem fixtures
SHA1_EMPTY = "da39a3ee5e6b4b0d3255bfef95601890afd80709"


@fixture
def fakefs_one_empty_file(fs):
    empty_file = Path("/") / "empty_file.txt"
    empty_file.touch(exist_ok=False)


@fixture
def persistent_minio_db():
    """start a MinIO db using Docker, persistent, for convience"""
    port = 9000
    cmdline = [
        "docker",
        "run",
        "--detach",
        f"--publish=9000:{port}",
        "--name=neogit_miniodb",
        f"minio/minio:{MINIO_VERSION}",
        "server",
        "/data",
    ]
    subprocess.check_call(cmdline)
    # ensure ready to receive connections
    time.sleep(2)


@fixture(scope="session")
def persistent_neo4j_db():
    """start a neo4j db using Docker"""
    cmdline = [
        "docker",
        "run",
        "--detach",
        "--publish=7474:7474",
        "--publish=7687:7687",
        "--env",
        "NEO4J_AUTH=none",
        "--env",
        'NEO4JLABS_PLUGINS=["apoc"]',
        "--name=neogit_neo4jdb",
        f"neo4j:{NEO4J_VERSION}",
    ]
    subprocess.check_call(cmdline)
    time.sleep(2)
