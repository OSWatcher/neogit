"""In-memory object storage adapter for testing"""

import os
from typing import Dict, Iterator, Tuple

from .abstract import (AbstractObjectStorage, Container, ContainerAlreadyExists, ContainerDoesNotExistError, Object,
                       StorageDriver)

# shared containers for all instances of FakeObjectStorage
# so that all thread will share the same objects
CONTAINERS: Dict[Container, Dict[str, Tuple[bytes, Object]]] = {}


class FakeObjectStorage(AbstractObjectStorage):
    def __init__(self, *args):
        print("here")
        self._storage_driver = StorageDriver()
        # obj name -> (data, metadata)
        global CONTAINERS
        self._containers = CONTAINERS

    def create_container(self, name: str) -> Container:
        if [c for c in self._containers.keys() if c.name == name]:
            raise ContainerAlreadyExists
        c = Container(name)
        self._containers[c] = {}
        return c

    def delete_container(self, container: Container) -> bool:
        del self._containers[container]
        return True

    def get_container(self, name: str) -> Container:
        try:
            return [c for c in self._containers.keys() if c.name == name][0]
        except IndexError:
            raise ContainerDoesNotExistError

    def upload_object(self, filepath: str, container: Container, object_name: str, extra: dict = None) -> Object:
        if extra is None:
            extra = {}
        with open(filepath, "rb") as f:
            data: bytes = f.read()
            size = os.stat(f.fileno()).st_size
            obj = Object(object_name, size, "", container, extra, {})
            self._containers[container][object_name] = (data, obj)
            return obj

    def download_object(self, obj: Object, destination_path: str, overwrite_existing: bool = False) -> bool:
        with open(destination_path, "wb") as f:
            data, metadata = self._containers[obj.container][obj.name]
            f.write(data)
            return True

    def get_object(self, container: Container, name: str) -> Object:
        _, obj = self._containers[container][name]
        return obj
