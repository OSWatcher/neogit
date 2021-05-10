from pathlib import Path

from pytest import fixture, raises

from neogit.config import ObjectConfig
from neogit.object_storage.abstract import ContainerAlreadyExists, ContainerDoesNotExistError
from neogit.object_storage.fake import FakeObjectStorage
from neogit.object_storage.lib_cloud import LibcloudObjectStorage


@fixture(
    params=[
        (FakeObjectStorage, ()),
        (
            LibcloudObjectStorage,
            (ObjectConfig("local", "/neogit", "objects"),)
        ),
    ]
)
def storage(fs, request):
    cls, cls_params = request.param
    # create directory for Libcloud object storage
    Path("/neogit").mkdir()
    adapter = cls(*cls_params)
    yield adapter


def test_create_container_ok(fs, storage):
    storage = FakeObjectStorage()
    container_name = "objects"
    c = storage.create_container(container_name)
    assert c.name == container_name


def test_create_container_already_exists(fs, storage):
    storage = FakeObjectStorage()
    container_name = "objects"
    storage.create_container(container_name)
    with raises(ContainerAlreadyExists):
        storage.create_container(container_name)


def test_get_container_not_exists(fs, storage):
    storage = FakeObjectStorage()
    with raises(ContainerDoesNotExistError):
        storage.get_container("not_exists")


def test_get_container_ok(fs, storage):
    storage = FakeObjectStorage()
    container_name = "objects"
    storage.create_container(container_name)
    c = storage.get_container(container_name)
    assert c.name == container_name


def test_upload_obj(fs, storage):
    # setup
    expected_data = b"data"
    with open("/file1.txt", "wb") as f:
        f.write(expected_data)
    storage = FakeObjectStorage()
    c = storage.create_container("objects")
    # test
    ret = storage.upload_object("/file1.txt", c, "file1")
    obj = storage.get_object(c, "file1")
    # assert
    assert ret
    ret = storage.download_object(obj, "/file2.txt")
    assert ret
    with open("/file2.txt", "rb") as f:
        data = f.read()
        assert expected_data == data
