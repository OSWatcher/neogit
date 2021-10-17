"""
Test Object Uploader

- upload 1/10/100/1000 files
- max workers 1/2/6/12/24
- TODO: upload one file already uploaded
- TODO: fault injection while uploading, retry logic
- TODO: inject KeyboardInterrupt, should remove every objects previously uploaded

"""
import hashlib
import itertools
import os
import random
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List
from unittest.mock import Mock

import pytest
from pytest import fixture

from neogit.config import settings
from neogit.merkle.uploader import MerkleFile, ObjectUploader
from neogit.object_storage import FakeObjectStorage, ObjectDoesNotExistError, TSObjectStorage


def sha1sum(data: bytes) -> str:
    hash = hashlib.sha1()
    hash.update(data)
    return hash.hexdigest()


@fixture(params=[1, 2, 12, 24], autouse=True, ids=lambda x: f"max_workers-{x}")
def uploader_max_workers(request):
    """Fixture to param uploader max workers threads
    autouse for all tests in this file"""
    # configure neogit
    max_workers: int = request.param
    settings.max_workers = max_workers


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


@fixture
def fake_ts_object_storage():
    ts_object_storage = TSObjectStorage(FakeObjectStorage, None)
    ts_object_storage.instance.create_container("objects")
    yield ts_object_storage
    # cleanup
    for container in ts_object_storage.instance.iterate_containers():
        ts_object_storage.instance.delete_container(container)


@pytest.mark.parametrize("file_count", [1, 10, 100])
def test_upload_file(fs, fake_ts_object_storage, file_count):
    # arrange
    # get first n elements
    file_list: List[MerkleFile] = list(itertools.islice(gen_file_list(), file_count))
    container = fake_ts_object_storage.instance.get_container("objects")
    # act
    with ObjectUploader(fake_ts_object_storage) as uploader:
        for file_to_upload in file_list:
            uploader.submit(file_to_upload.filepath, file_to_upload.hash)
    # assert
    for file_to_upload in file_list:
        obj = fake_ts_object_storage.instance.get_object(container, file_to_upload.hash)
        assert obj
        with NamedTemporaryFile() as tmp_file:
            fake_ts_object_storage.instance.download_object(obj, tmp_file.name)
            with open(tmp_file.name, "rb") as f:
                content = f.read()
                assert sha1sum(content) == file_to_upload.hash


def test_check_exception(fs):
    """Check that check_exception API raise an exception when one thread encounters a fatal error"""
    # arrange
    object_to_upload: MerkleFile = list(itertools.islice(gen_file_list(), 1))[0]
    # get object should raise that the object cannot be found
    mock_fake_ts_object_storage = Mock()
    mock_fake_ts_object_storage.instance.get_object.side_effect = ObjectDoesNotExistError()
    mock_fake_ts_object_storage.instance.upload_object_via_stream.side_effect = ConnectionError("Connection Error !")
    # act
    uploader = ObjectUploader(mock_fake_ts_object_storage)
    uploader.submit(object_to_upload.filepath, object_to_upload.hash)
    uploader.wait()
    # assert
    with pytest.raises(ConnectionError):
        uploader.check_exception()


# TODO
# def test_upload_file_already_existing(fs, fake_ts_object_storage):
#     # arrange
#     object_to_upload = list(itertools.islice(gen_file_list(), 1))[0]
#     container = fake_ts_object_storage.instance.get_container("objects")
#     # upload first time
#     uploader = ObjectUploader(fake_ts_object_storage)
#     uploader.submit(object_to_upload.filepath, object_to_upload.hash)
#     # act
#     # upload twice
#     uploader.submit(object_to_upload.filepath, object_to_upload.hash)
#     uploader.wait()
#     # assert
#     # ????
