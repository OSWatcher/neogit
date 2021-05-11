from pathlib import Path

from pytest import fixture, raises

from neogit.config import ObjectConfig
from neogit.object_storage.abstract import ContainerAlreadyExists, ContainerDoesNotExistError
from neogit.object_storage.fake import FakeObjectStorage
from neogit.object_storage.lib_cloud import LibcloudObjectStorage


@fixture
def fake_adapter(fs):
    key = "/neogit"
    Path(key).mkdir(parents=True)
    config = ObjectConfig(provider="local", key=key)
    storage = LibcloudObjectStorage(config)
    yield storage
    # cleanup
    for container in storage.iterate_containers():
        storage.delete_container(container)


def test_create_container_ok(fake_adapter):
    container_name = "objects"
    c = fake_adapter.create_container(container_name)
    assert c.name == container_name


def test_create_container_already_exists(fake_adapter):
    container_name = "objects"
    fake_adapter.create_container(container_name)
    with raises(ContainerAlreadyExists):
        fake_adapter.create_container(container_name)


def test_get_container_not_exists(fake_adapter):
    with raises(ContainerDoesNotExistError):
        fake_adapter.get_container("not_exists")


def test_get_container_ok(fake_adapter):
    container_name = "objects"
    fake_adapter.create_container(container_name)
    c = fake_adapter.get_container(container_name)
    assert c.name == container_name


def test_upload_obj(fs, fake_adapter):
    # setup
    expected_data = b"data"
    with open("/file1.txt", "wb") as f:
        f.write(expected_data)
    fake_adapter = FakeObjectStorage()
    c = fake_adapter.create_container("objects")
    # test
    ret = fake_adapter.upload_object("/file1.txt", c, "file1")
    obj = fake_adapter.get_object(c, "file1")
    # assert
    assert ret
    ret = fake_adapter.download_object(obj, "/file2.txt")
    assert ret
    with open("/file2.txt", "rb") as f:
        data = f.read()
        assert expected_data == data
