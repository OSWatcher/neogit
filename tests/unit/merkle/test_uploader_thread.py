import itertools
from queue import Queue
from tempfile import NamedTemporaryFile

from neogit.core.model import FSFileNode, MerkleLabel, MerkleNode
from neogit.core.visitor import VisitedNode
from neogit.merkle.uploader import MerkleFile
from neogit.merkle.uploaderthread import ObjectUploaderThread
from tests.conftest import gen_file_list, sha1sum


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
