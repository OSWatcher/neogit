import hashlib
import itertools
import os
import random
from pathlib import Path
from queue import Queue
from tempfile import NamedTemporaryFile

import pytest

from neogit.core.model import FSFileNode, MerkleLabel, MerkleNode
from neogit.core.visitor import VisitedNode
from neogit.merkle.uploader import MerkleFile
from neogit.merkle.uploaderthread import ObjectUploaderThread
from neogit.object_storage import FakeObjectStorage, TSObjectStorage


def sha1sum(data: bytes) -> str:
    hash = hashlib.sha1()
    hash.update(data)
    return hash.hexdigest()


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


@pytest.fixture
def fake_ts_object_storage():
    ts_object_storage = TSObjectStorage(FakeObjectStorage, None)
    ts_object_storage.instance.create_container("objects")
    yield ts_object_storage
    # cleanup
    for container in ts_object_storage.instance.iterate_containers():
        ts_object_storage.instance.delete_container(container)


def test_uploader_thread(fs, fake_ts_object_storage):
    # arrange
    queue = Queue()
    container = fake_ts_object_storage.instance.get_container("objects")
    object_to_upload: MerkleFile = list(itertools.islice(gen_file_list(), 1))[0]
    visited_node = VisitedNode(
        FSFileNode(object_to_upload.filepath), MerkleNode(object_to_upload.hash, MerkleLabel.Blob)
    )
    queue.put(visited_node)
    queue.put(None)
    # act
    with ObjectUploaderThread(fake_ts_object_storage, queue) as uploader_thread:
        uploader_thread.start()
        uploader_thread.join()
    # assert
    obj = fake_ts_object_storage.instance.get_object(container, object_to_upload.hash)
    assert obj
    with NamedTemporaryFile() as tmp_file:
        fake_ts_object_storage.instance.download_object(obj, tmp_file.name)
        with open(tmp_file.name, "rb") as f:
            content = f.read()
            assert sha1sum(content) == object_to_upload.hash
