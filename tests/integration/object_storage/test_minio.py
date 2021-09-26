import pytest
from pytest import raises

from neogit.object_storage.abstract import ContainerAlreadyExists, ContainerDoesNotExistError


def test_create_container_ok(clean_minio_db):
    container_name = "objects"
    c = clean_minio_db.create_container(container_name)
    assert c.name == container_name


def test_create_container_already_exists(clean_minio_db):
    container_name = "objects"
    clean_minio_db.create_container(container_name)
    with raises(ContainerAlreadyExists):
        clean_minio_db.create_container(container_name)


def test_get_container_not_exists(clean_minio_db):
    with raises(ContainerDoesNotExistError):
        clean_minio_db.get_container("not_exists")


def test_get_container_ok(clean_minio_db):
    container_name = "objects"
    clean_minio_db.create_container(container_name)
    c = clean_minio_db.get_container(container_name)
    assert c.name == container_name


@pytest.mark.skip(reason="libcloud returns ObjectHashMismatchError")
def test_upload_obj(fs, clean_minio_db):
    """writes file in fake filesystem, upload it to DB, and assert that we receive it"""
    # setup
    expected_data = b"data"
    with open("/file1.txt", "wb") as f:
        f.write(expected_data)
    adapter = clean_minio_db
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


def test_upload_obj2(tmp_path, clean_minio_db):
    """writes file in fake filesystem, upload it to DB, and assert that we receive it"""
    # setup
    expected_data = b"data"
    with open(tmp_path / "file1.txt", "wb") as f:
        f.write(expected_data)
    adapter = clean_minio_db
    c = adapter.create_container("objects")
    # test
    ret = adapter.upload_object(tmp_path / "file1.txt", c, "file1")
    obj = adapter.get_object(c, "file1")
    # assert
    assert ret
    ret = adapter.download_object(obj, tmp_path / "file2.txt")
    assert ret
    with open(tmp_path / "file2.txt", "rb") as f:
        data = f.read()
        assert expected_data == data
