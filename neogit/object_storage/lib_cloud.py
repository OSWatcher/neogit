import threading
from typing import Dict

from libcloud.storage.base import Container as LibCloudContainer
from libcloud.storage.base import Object as LibCloudObject
from libcloud.storage.providers import get_driver
from libcloud.storage.types import ContainerAlreadyExistsError as LibCloudContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError as LibCloudContainerDoesNotExistError

from neogit.object_storage.abstract import (AbstractObjectStorage, Container, ContainerAlreadyExists,
                                            ContainerDoesNotExistError, Object)


class LibcloudObjectStorage(AbstractObjectStorage):
    def __init__(self, provider: str, key: str):
        cls = get_driver(provider)
        self._driver = cls(key)

    def create_container(self, name: str) -> Container:
        try:
            c: LibCloudContainer = self._driver.create_container(name)
        except LibCloudContainerAlreadyExistsError:
            raise ContainerAlreadyExists
        else:
            return Container(c.name)

    def get_container(self, name: str) -> Container:
        try:
            c: LibCloudContainer = self._driver.get_container(name)
        except LibCloudContainerDoesNotExistError:
            raise ContainerDoesNotExistError
        else:
            return Container(c.name)

    def upload_object(self, filepath: str, container: Container, object_name: str, extra: dict = None) -> Object:
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        obj: LibCloudObject = self._driver.upload_object(filepath, libcloud_container, object_name, extra, True)
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)

    def download_object(self, obj: Object, destination_path: str, overwrite_existing: bool = False) -> bool:
        libcloud_container = LibCloudContainer(obj.container.name, {}, self._driver)
        libcloud_object = LibCloudObject(
            obj.name, obj.size, obj.hash, obj.extra, obj.meta_data, libcloud_container, self._driver
        )
        return self._driver.download_object(libcloud_object, destination_path, overwrite_existing)

    def get_object(self, container: Container, name: str) -> Object:
        obj: LibCloudObject = self._driver.get_object(container.name, name)
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)


class TSLibCloudObjectStorage:
    """Thread safe provider for Libcloud object storage.

    Return a per-thread instance
    """

    def __init__(self, provider: str, key: str):
        self._provder = provider
        self._key = key
        self._instances: Dict[int, LibcloudObjectStorage] = {}

    @property
    def instance(self) -> LibcloudObjectStorage:
        tid = threading.get_ident()
        try:
            inst = self._instances[tid]
        except KeyError:
            inst = LibcloudObjectStorage(self._provder, self._key)
            self._instances[tid] = inst
        return inst
