from pytest import fixture, raises

from neogit.config import ObjectConfig, settings
from neogit.object_storage.abstract import ContainerAlreadyExists, ContainerDoesNotExistError
from neogit.object_storage.fake import FakeObjectStorage
from neogit.object_storage.lib_cloud import LibcloudObjectStorage


@fixture
def adapter(minio_db):
    config = ObjectConfig.from_settings(settings)
    storage = LibcloudObjectStorage(config)
    yield storage
    # cleanup
    for container in storage.iterate_containers():
        storage.delete_container(container)


def test_create_container_ok(adapter):
    container_name = "objects"
    c = adapter.create_container(container_name)
    assert c.name == container_name


def test_create_container_already_exists(adapter):
    container_name = "objects"
    adapter.create_container(container_name)
    with raises(ContainerAlreadyExists):
        adapter.create_container(container_name)


def test_get_container_not_exists(adapter):
    with raises(ContainerDoesNotExistError):
        adapter.get_container("not_exists")


def test_get_container_ok(adapter):
    container_name = "objects"
    adapter.create_container(container_name)
    c = adapter.get_container(container_name)
    assert c.name == container_name


def test_upload_obj(fs, adapter):
    # setup
    expected_data = b"data"
    with open("/file1.txt", "wb") as f:
        f.write(expected_data)
    adapter = FakeObjectStorage()
    c = adapter.create_container("objects")
    # test
    ret = adapter.upload_object("/file1.txt", c, "file1")
    obj = adapter.get_object(c, "file1")
    # assert
    assert ret
    ret = adapter.download_object(obj, "/file2.txt")
    assert ret
    with open("/file2.txt", "rb") as f:
        data = f.read()
        assert expected_data == data
