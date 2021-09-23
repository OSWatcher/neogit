"""pytest configuration and fixtures"""

import logging
import random
import string
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Optional
from urllib.error import URLError
from urllib.request import urlopen

from neo4j import BoltDriver, GraphDatabase
from neomodel import db as neomodel_db
from pytest import fixture

from neogit.config import ObjectConfig, settings
from neogit.object_storage import FakeObjectStorage, LibcloudObjectStorage, TSObjectStorage

NEO4J_VERSION = "4.2.4"
MINIO_VERSION = "RELEASE.2021-05-11T23-27-41Z"
DEFAULT_USERNAME = "neo4j"
DEFAULT_PASSWORD = "admin"
TEST_DATA = Path(__file__).parent / "data"
TEST_DATA_FS = TEST_DATA / "fs"
TEST_DATA_FS_DIR_EMPTY = TEST_DATA_FS / "dir_empty"
ROOT_REPO = Path(__file__).parent.parent
DEFAULT_NEO4J_DB_NAME = "neogit_neo4j_testdb"
DEFAULT_MINIO_DB_NAME = "neogit_minio_testdb"


def pytest_addoption(parser):
    """add a new option to pass a specific directory to be merkelized"""
    parser.addoption("--repo", action="store", help="root directory to be indexed")
    parser.addoption(
        "--persistdb",
        action="store_true",
        default=False,
        help="do not remove container at the end of the integration tests, and reuse them for the next run",
    )


@fixture
def arg_repo_root(pytestconfig):
    return pytestconfig.getoption("repo")


def random_name():
    """Generates a random name"""
    length = 8
    return "".join(random.choices(string.ascii_lowercase, k=length))


# Neo4j fixtures


@dataclass
class Neo4jDriver:
    driver: Optional[BoltDriver]


@fixture(scope="session")
def start_neo4j_db(pytestconfig):
    """start a neo4j db using Docker"""
    # choose random name or default name if persistent
    if not pytestconfig.getoption("persistdb"):
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
    else:
        cont_name = DEFAULT_NEO4J_DB_NAME
        # ensure previous db is started
        cmdline = ["docker", "start", cont_name]
    subprocess.check_call(cmdline)
    # update dynaconf settings for tests
    settings.neo4j.proto = "bolt"
    settings.neo4j.host = "localhost"
    settings.neo4j.port = 7687
    settings.neo4j.user = "neo4j"
    settings.neo4j.password = "neo4j"
    # set neomodel config url
    neomodel_db.set_connection(settings.neo4j.url_full)
    yield cont_name
    if not pytestconfig.getoption("persistdb"):
        cmdline = ["docker", "rm", "--force", cont_name]
        subprocess.check_call(cmdline)


@fixture(scope="session")
def neo4j_ready(start_neo4j_db: str):
    """ensure neo4jdb is ready"""
    container_name = start_neo4j_db
    neo4j_http_url = settings.neo4j.http_url
    opened = False
    while not opened:
        try:
            logging.info("attempting to connect to DB %s", neo4j_http_url)
            with urlopen(neo4j_http_url, timeout=1) as opened_url:
                opened_url.read()
        except (URLError, ConnectionError):
            time.sleep(0.7)
        else:
            opened = True
    yield container_name


@fixture(scope="session")
def neo4j_con(neo4j_ready: str):
    # start db connection with the most basic driver
    bolt_url = settings.neo4j.url
    creds = (settings.neo4j.user, settings.neo4j.password)
    driver = GraphDatabase.driver(bolt_url, auth=creds)
    yield driver


@fixture(scope="function")
def clean_neo4j_db(neo4j_con: BoltDriver):
    """cleanup db after test"""
    driver = neo4j_con
    # ensure it's cleaned before test
    with driver.session() as session:
        # clean all nodes and relationships
        session.run("MATCH (n) DETACH DELETE n")
    yield driver
    # cleanup
    with driver.session() as session:
        # clean all nodes and relationships
        session.run("MATCH (n) DETACH DELETE n")


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
def minio_db(pytestconfig):
    """start a MinIO db using Docker"""
    # choose random name or default name if persistent
    provider = "minio"
    key = "minioadmin"
    secret = "minioadmin"
    port = 9000
    host = "127.0.0.1"
    secure = False
    if not pytestconfig.getoption("persistdb"):
        cont_name = random_name()
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
    else:
        cont_name = DEFAULT_MINIO_DB_NAME
        cmdline = ["docker", "start", cont_name]
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
    if not pytestconfig.getoption("persistdb"):
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
