"""pytest configuration and fixtures"""
import hashlib
import logging
import os
import random
import string
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Dict, Iterator, Optional, Union
from urllib.error import URLError
from urllib.request import urlopen

import attr
import pytest
from neo4j import BoltDriver, GraphDatabase
from neomodel import db as neomodel_db
from pytest import fixture
from requests.exceptions import ConnectionError

from neogit.config import ObjectConfig, settings
from neogit.core.model import MerkleLabel, MerkleNode
from neogit.merkle.uploader import MerkleFile
from neogit.object_storage import FakeObjectStorage, LibcloudObjectStorage, ObjectStorageError, TSObjectStorage
from neogit.service import Neogit

NEO4J_VERSION = "4.4.30"
MINIO_VERSION = "RELEASE.2024-02-13T15-35-11Z"
DEFAULT_USERNAME = "neo4j"
DEFAULT_PASSWORD = "admin"
TEST_DATA = Path(__file__).parent / "data"
TEST_DATA_FS = TEST_DATA / "fs"
TEST_DATA_FS_DIR_EMPTY = TEST_DATA_FS / "dir_empty"
ROOT_REPO = Path(__file__).parent.parent
DEFAULT_NEO4J_DB_NAME = "neogit_neo4j_testdb"
DEFAULT_MINIO_DB_NAME = "neogit_minio_testdb"


def pytest_configure(config):
    # Set Neo4j and urllib3 loggers to WARNING to silence INFO and DEBUG messages
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("git.cmd").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

    # Silence deprecation warnings from third-party libraries
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="libcloud.common.aws")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="neo4j._sync.driver")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="neomodel.properties")


def pytest_addoption(parser):
    parser.addoption("--repo", action="store", default=None, help="root directory to be indexed")
    parser.addoption(
        "--persistdb",
        action="store_true",
        default=False,
        help="do not remove container at the end of the integration tests, and reuse them for the next run",
    )
    parser.addoption(
        "--externdb",
        action="store_true",
        default=False,
        help="do not create required containers (Neo4j/MinIO) with Docker. Use the provided values (and environment "
        "variables) instead. Useful to run the integration tests in Github Actions where the services containers "
        "already provides the databases we need.",
    )
    parser.addoption(
        "--minio-volume",
        action="store_true",
        default=False,
        help="set a local path to be mounted as the main data volume for MiniIO Docker instance",
    )


@fixture
def arg_repo_root(pytestconfig):
    return pytestconfig.getoption("repo")


# helpers


def sha1sum(data: bytes) -> str:
    hash = hashlib.sha1()
    hash.update(data)
    return hash.hexdigest()


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
    if pytestconfig.getoption("externdb"):
        # do not create or start any container, just return None
        yield
        return
    # choose random name or default name if persistent
    if not pytestconfig.getoption("persistdb"):
        cont_name = random_name()
    else:
        cont_name = DEFAULT_NEO4J_DB_NAME
    # try to start it
    cmdline = ["docker", "start", cont_name]
    try:
        subprocess.check_call(cmdline)
    except subprocess.CalledProcessError:
        # create it
        cmdline = [
            "docker",
            "run",
            "--detach",
            "--publish=7474:7474",
            "--publish=7687:7687",
            "--env",
            "NEO4J_AUTH=none",
            f"--name={cont_name}",
            f"neo4j:{NEO4J_VERSION}",  # noqa: E231
        ]
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
def ready_neo4j(start_neo4j_db: Optional[str]):
    """ensure neo4jdb is ready"""
    container_name = start_neo4j_db
    neo4j_http_url = settings.neo4j.http_url
    opened = False
    while not opened:
        try:
            logging.info("attempting to connect to DB %s", neo4j_http_url)
            with urlopen(neo4j_http_url, timeout=1) as opened_url:
                opened_url.read()
        except (URLError, ConnectionError, ConnectionResetError):
            time.sleep(0.7)
        else:
            opened = True
    yield container_name


@fixture(scope="class")
def clean_neo4j_db_per_class(ready_neo4j: Optional[str]):
    """cleanup db after test"""
    with clean_neo4j_db_impl() as driver:
        yield driver


@fixture(scope="function")
def clean_neo4j_db(ready_neo4j: Optional[str]):
    """cleanup db after test"""
    with clean_neo4j_db_impl() as driver:
        yield driver


@contextmanager
def clean_neo4j_db_impl():
    """common implementation for same fixture with different scopes"""
    bolt_url = settings.neo4j.url
    creds = tuple(settings.neo4j.creds) if settings.neo4j.creds is not None else None
    driver = GraphDatabase.driver(bolt_url, auth=creds)
    # ensure it's cleaned before test
    with driver.session() as session:
        # clean all nodes and relationships
        session.run("MATCH (n) DETACH DELETE n")
    try:
        yield driver
    finally:
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
    with init_libcloud_object_storage_impl() as tmp_path:
        yield tmp_path


@fixture(scope="module")
def init_libcloud_object_storage_per_module():
    with init_libcloud_object_storage_impl() as tmp_path:
        yield tmp_path


@contextmanager
def init_libcloud_object_storage_impl():
    """common implementation for same fixture with different scopes"""
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
    provider = "minio"
    # whatever happens next, make sure that we forced minio
    settings.object.provider = provider
    if pytestconfig.getoption("externdb"):
        # do not create or start any container
        yield
        return
    # choose random name or default name if persistent
    key = "minioadmin"
    secret = "minioadmin"
    port = 9000
    host = "127.0.0.1"
    secure = False
    if not pytestconfig.getoption("persistdb"):
        cont_name = random_name()
    else:
        cont_name = DEFAULT_MINIO_DB_NAME
    # try to start container
    cmdline = ["docker", "start", cont_name]
    try:
        subprocess.check_call(cmdline)
    except subprocess.CalledProcessError:
        # assume docker start failed because container doesn't exist
        # create it
        cmdline = [
            "docker",
            "run",
            "--detach",
            f"--publish=9000:{port}",
            "--publish=9001:9001",
            f"--name={cont_name}",
        ]
        if pytestconfig.getoption("minio_volume"):
            host_path = pytestconfig.getoption("minio_volume")
            cmdline.extend(
                [
                    "--volume",
                    f"{host_path}:/data",  # noqa: E231
                ]
            )
        cmdline.extend(
            [
                f"minio/minio:{MINIO_VERSION}",
                "server",
                "/data",
                # minio web console uses a dynamic port by default
                # force console to redirect to 9001
                "--console-address",
                ":9001",
            ]
        )
        subprocess.check_call(cmdline)
    # update settings
    settings.object.provider = provider
    settings.object.key = key
    settings.object.secret_key = secret
    settings.object.host = host
    settings.object.port = port
    settings.object.secure = secure
    yield
    if not pytestconfig.getoption("persistdb"):
        cmdline = ["docker", "rm", "--force", cont_name]
        subprocess.check_call(cmdline)


@fixture(scope="session")
def ready_minio_db(minio_db):
    """ensures that the minioDB is ready to receive connections"""
    config = ObjectConfig.from_settings(settings)
    driver = None
    while driver is None:
        try:
            driver = LibcloudObjectStorage(config)
            list(driver.iterate_containers())
        except (ConnectionError, ObjectStorageError):
            driver = None
            time.sleep(0.1)
    return driver


@fixture(scope="function")
def clean_minio_db(ready_minio_db):
    """cleanup DB after test"""
    with clean_minio_db_impl(ready_minio_db) as libcloud_drv:
        yield libcloud_drv


@fixture(scope="class")
def clean_minio_db_per_class(ready_minio_db):
    """cleanup DB after test"""
    with clean_minio_db_impl(ready_minio_db) as libcloud_drv:
        yield libcloud_drv


@contextmanager
def clean_minio_db_impl(ready_minio_db):
    """common implementation for same fixture with different scopes"""
    libcloud_drv = ready_minio_db

    # ensure cleanup up before test if pytest crashed or process killed, or teardown skipped for whatever reason
    def cleanup_db():
        for container in libcloud_drv.iterate_containers():
            for obj in libcloud_drv.iterate_container_objects(container):
                libcloud_drv.delete_object(obj)
            libcloud_drv.delete_container(container)

    cleanup_db()
    # do the test
    try:
        yield libcloud_drv
    finally:
        # cleanup
        cleanup_db()


# fake filesystem fixtures
SHA1_EMPTY = "da39a3ee5e6b4b0d3255bfef95601890afd80709"


@fixture
def fakefs_one_empty_file(fs):
    empty_file = Path("/") / "empty_file.txt"
    empty_file.touch(exist_ok=False)


# instantiate Neogit
@fixture(scope="function", params=[1, os.cpu_count(), os.cpu_count() * 2], ids=lambda val: f"workers-{val}")
def max_workers(request):
    nb_workers = request.param
    return nb_workers


@fixture(scope="class", params=[1, os.cpu_count(), os.cpu_count() * 2], ids=lambda val: f"workers-{val}")
def max_workers_per_class(request):
    nb_workers = request.param
    return nb_workers


@fixture(
    scope="function", params=[None, "local", "minio"], ids=["FakeObjectStorage", "LibCloud-Local", "LibCloud-MinIO"]
)
def neogit(clean_neo4j_db, clean_minio_db, tmp_path, max_workers, request):
    """creates an instance of Neogit, inject a fake object storage as dependency"""
    provider = request.param
    config = None
    cls = LibcloudObjectStorage
    if provider is None:
        cls = FakeObjectStorage
    if provider == "local":
        config = ObjectConfig(provider=provider, key=str(tmp_path))
    if provider == "minio":
        config = ObjectConfig.from_settings(settings)
    settings.max_workers = max_workers
    ts_obj = TSObjectStorage(cls, config)
    neogit = Neogit(ts_obj)
    return neogit


@pytest.fixture(scope="class")
def tmp_path_per_class():
    with TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@fixture(scope="class", params=[None, "local", "minio"], ids=["FakeObjectStorage", "LibCloud-Local", "LibCloud-MinIO"])
def neogit_per_class(
    clean_neo4j_db_per_class, clean_minio_db_per_class, tmp_path_per_class, max_workers_per_class, request
):
    provider = request.param
    config = None
    cls = LibcloudObjectStorage
    if provider is None:
        cls = FakeObjectStorage
    if provider == "local":
        config = ObjectConfig(provider=provider, key=str(tmp_path_per_class))
    if provider == "minio":
        config = ObjectConfig.from_settings(settings)
    settings.max_workers = max_workers_per_class
    ts_obj = TSObjectStorage(cls, config)
    neogit = Neogit(ts_obj)
    return neogit


@fixture(scope="function")
def neogit_init(neogit):
    neogit.init()
    return neogit


@fixture(scope="class")
def neogit_init_per_class(neogit_per_class):
    neogit = neogit_per_class
    neogit.init()
    return neogit


# object storage fixture
#
# generate multiple object storage
# --------------------------------------------


@fixture(scope="class", params=[None, "local", "minio"], ids=["FakeObjectStorage", "LibCloud-Local", "LibCloud-MinIO"])
def ts_object_storage(
    clean_neo4j_db_per_class, clean_minio_db_per_class, tmp_path_per_class, max_workers_per_class, request
):
    provider = request.param
    config = None
    cls = LibcloudObjectStorage
    if provider is None:
        cls = FakeObjectStorage
    if provider == "local":
        config = ObjectConfig(provider=provider, key=str(tmp_path_per_class))
    if provider == "minio":
        config = ObjectConfig.from_settings(settings)
    settings.max_workers = max_workers_per_class
    ts_obj = TSObjectStorage(cls, config)
    yield ts_obj


@fixture
def fake_ts_object_storage():
    # Clear global state before creating instance (FakeObjectStorage uses global CONTAINERS dict)
    from neogit.object_storage.fake import CONTAINERS
    CONTAINERS.clear()

    ts_object_storage = TSObjectStorage(FakeObjectStorage, None)
    ts_object_storage.instance.create_container("objects")
    yield ts_object_storage
    # cleanup
    for container in ts_object_storage.instance.iterate_containers():
        ts_object_storage.instance.delete_container(container)


# root_fs
#
# fixture related to generating a virtual root_fs populated with files and directories
# --------------------------------------------------------------------------------------
EMPTY_SHA1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"


@attr.s
class VirtualFSBlob:
    content: bytes = attr.ib()


@attr.s
class VirtualFSDirectory:
    merkeled_node: MerkleNode = attr.ib()
    children: Dict[str, Union["VirtualFSDirectory", VirtualFSBlob]] = attr.ib(factory=dict)


def gen_root_fs() -> Iterator[VirtualFSDirectory]:
    """This generator will yield every filesystem representation for each
    test that we want to perform on the MerkleTree generator.

    Each VirtualFSDirectory also contains its merkle_node representation"""
    # root
    root_merkle_node = MerkleNode(EMPTY_SHA1, label=MerkleLabel.Tree)
    root_dir = VirtualFSDirectory(root_merkle_node)
    yield pytest.param(root_dir, id="empty_dir")
    # one subdirectory
    subdir1_merkle_node = MerkleNode(EMPTY_SHA1, label=MerkleLabel.Tree)
    subdir1 = VirtualFSDirectory(subdir1_merkle_node)
    root_dir.merkeled_node.hash = "ac7b58cb43a320c493188b1a976a27f94a4e53ea"
    root_dir.children["subdir1"] = subdir1
    yield pytest.param(root_dir, id="one_subdir")
    # one file
    one_file_merkle_node = MerkleNode(EMPTY_SHA1, MerkleLabel.Tree)
    one_file_blob = VirtualFSBlob(b"")
    root_dir.children.clear()
    root_dir.children["one_file"] = one_file_blob
    root_dir.merkeled_node.hash = "b506c80ee672b2f4971b25ca8ddad8fbd1e7281f"
    root_dir.merkeled_node.children.clear()
    root_dir.merkeled_node.children["one_file"] = one_file_merkle_node
    yield pytest.param(root_dir, id="one_file")


@fixture(params=list(gen_root_fs()))
def root_fs(fs, request):
    root_dir: VirtualFSDirectory = request.param

    def build_fs(directory: VirtualFSDirectory, current_path: Path):
        """Build a filesystem recursively from it's representation"""
        # build current dir
        current_path.mkdir(exist_ok=True)
        # build children
        for child_name, child in directory.children.items():
            child_path = current_path / child_name
            if isinstance(child, VirtualFSBlob):
                child_path.touch()
            else:
                build_fs(child, child_path)

    build_fs(root_dir, Path("/"))
    return root_dir.merkeled_node


# gen file list
def gen_file_list():
    """Generate a list of files"""
    # We don't delete the files here
    # so make sure to request the virtual filesystem fixture "fs", so
    # it won't remain for real
    while True:
        with NamedTemporaryFile(delete=False) as tmp_file:
            # write random data
            # of random size
            rand_size = random.randint(1, 1024)
            data = os.urandom(rand_size)
            tmp_file.file.write(data)
            tmp_file.flush()
            yield MerkleFile(Path(tmp_file.name), sha1sum(data))
