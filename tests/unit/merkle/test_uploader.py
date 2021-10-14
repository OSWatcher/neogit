"""
Test Object Uploader

- upload one file
- upload one file already uploaded
- upload 10/100/1000 files
- max workers 1/2/6/12/24
- fault injection while uploading, retry logic
- inject KeyboardInterrupt, should remove every objects previously uploaded

"""
import hashlib
from pathlib import Path

from pytest import fixture

from neogit.merkle.uploader import ObjectUploader
from neogit.object_storage import FakeObjectStorage, TSObjectStorage


@fixture
def fake_ts_object_storage():
    ts_object_storage = TSObjectStorage(FakeObjectStorage, None)
    ts_object_storage.instance.create_container("objects")
    yield ts_object_storage
    # cleanup
    for container in ts_object_storage.instance.iterate_containers():
        ts_object_storage.instance.delete_container(container)


def test_upload_one_file(fs, fake_ts_object_storage):
    # arrange
    expected_data = b"data"
    hash = hashlib.sha1()
    hash.update(expected_data)
    expected_data_hash = hash.hexdigest()
    filepath = Path("/file1.txt")
    with open(filepath, "wb") as f:
        f.write(expected_data)
    container = fake_ts_object_storage.instance.get_container("objects")
    # act
    with ObjectUploader(fake_ts_object_storage) as uploader:
        uploader.submit(filepath, expected_data_hash)
    # assert
    obj = fake_ts_object_storage.instance.get_object(container, expected_data_hash)
    assert obj
    fake_ts_object_storage.instance.download_object(obj, "/file2.txt")
    with open("/file2.txt", "rb") as f:
        content = f.read()
        assert content, expected_data
