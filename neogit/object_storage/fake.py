"""In-memory object storage adapter for testing"""

import os
import threading
from typing import Dict, Tuple

from .abstract import (AbstractObjectStorage, Container, ContainerAlreadyExists, ContainerDoesNotExistError, Object,
                       StorageDriver)

lock = threading.Lock()


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ContainerSingleton(metaclass=Singleton):
    """Fake container with a singleton so all threads share the same containers"""

    def __init__(self):
        self._containers: Dict[Container, Dict[str, Tuple[bytes, Object]]] = {}

    def __getitem__(self, item):
        return self._containers[item]

    def __setitem__(self, key, value):
        self._containers[key] = value

    def keys(self):
        return self._containers.keys()


class FakeObjectStorage(AbstractObjectStorage):
    def __init__(self, *args):
        print("here")
        self._storage_driver = StorageDriver()
        # obj name -> (data, metadata)
        self._container_singleton = ContainerSingleton()

    def create_container(self, name: str) -> Container:
        if [c for c in self._container_singleton.keys() if c.name == name]:
            raise ContainerAlreadyExists
        c = Container(name)
        self._container_singleton[c] = {}
        return c

    def get_container(self, name: str) -> Container:
        try:
            return [c for c in self._container_singleton.keys() if c.name == name][0]
        except IndexError:
            raise ContainerDoesNotExistError

    def upload_object(self, filepath: str, container: Container, object_name: str, extra: dict = None) -> Object:
        if extra is None:
            extra = {}
        with open(filepath, "rb") as f:
            data: bytes = f.read()
            size = os.stat(f.fileno()).st_size
            obj = Object(object_name, size, "", container, extra, {})
            self._container_singleton[container][object_name] = (data, obj)
            return obj

    def download_object(self, obj: Object, destination_path: str, overwrite_existing: bool = False) -> bool:
        with open(destination_path, "wb") as f:
            data, metadata = self._container_singleton[obj.container][obj.name]
            f.write(data)
            return True

    def get_object(self, container: Container, name: str) -> Object:
        _, obj = self._container_singleton[container][name]
        return obj
