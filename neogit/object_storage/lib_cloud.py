from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from libcloud.storage.base import Container as LibCloudContainer
from libcloud.storage.base import Object as LibCloudObject
from libcloud.storage.drivers.local import LocalStorageDriver
from libcloud.storage.providers import get_driver
from libcloud.storage.types import ContainerAlreadyExistsError as LibCloudContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError as LibCloudContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError as LibCloudObjectDoesNotExistError

from neogit.config import ObjectConfig
from neogit.object_storage.abstract import (
    AbstractObjectStorage,
    Container,
    ContainerAlreadyExists,
    ContainerDoesNotExistError,
    Object,
    ObjectDoesNotExistError,
)


class LibcloudObjectStorage(AbstractObjectStorage):
    def __init__(self, config: ObjectConfig):
        cls = get_driver(config.provider)
        # local provider: ensure directory is created
        if cls == LocalStorageDriver:
            Path(config.key).mkdir(parents=True, exist_ok=True)
        # drop all keys whose values is None
        config_dict = {k: v for k, v in asdict(config).items() if v is not None}
        # drop provider as well (already used before)
        del config_dict["provider"]
        print(config_dict)
        self._driver = cls(**config_dict)

    def create_container(self, name: str) -> Container:
        try:
            c: LibCloudContainer = self._driver.create_container(name)
        except LibCloudContainerAlreadyExistsError:
            raise ContainerAlreadyExists
        else:
            return Container(c.name)

    def delete_container(self, container: Container) -> bool:
        """Delete a container and all it's objects"""
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        # 1. ensure all objects are deleted
        for obj in self._driver.iterate_container_objects(libcloud_container):
            self._driver.delete_object(obj)
        # 2. delete container
        try:
            self._driver.delete_container(libcloud_container)
        except LibCloudContainerDoesNotExistError:
            return False
        else:
            return True

    def iterate_containers(self) -> Iterator[Container]:
        gen_containers = (Container(c.name) for c in self._driver.iterate_containers())
        yield from gen_containers

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

    def upload_object_via_stream(
        self, iterator: Iterator[bytes], container: Container, object_name: str, extra: dict = None
    ) -> Object:
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        obj: LibCloudObject = self._driver.upload_object_via_stream(iterator, libcloud_container, object_name, extra)
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)

    def download_object(self, obj: Object, destination_path: str, overwrite_existing: bool = False) -> bool:
        libcloud_container = LibCloudContainer(obj.container.name, {}, self._driver)
        libcloud_object = LibCloudObject(
            obj.name, obj.size, obj.hash, obj.extra, obj.meta_data, libcloud_container, self._driver
        )
        return self._driver.download_object(libcloud_object, destination_path, overwrite_existing)

    def download_object_as_stream(self, obj: Object, chunk_size: int = None) -> Iterator[bytes]:
        libcloud_container = LibCloudContainer(obj.container.name, {}, self._driver)
        libcloud_object = LibCloudObject(
            obj.name, obj.size, obj.hash, obj.extra, obj.meta_data, libcloud_container, self._driver
        )
        yield from self._driver.download_object_as_stream(libcloud_object, chunk_size)

    def get_object(self, container: Container, name: str) -> Object:
        try:
            obj: LibCloudObject = self._driver.get_object(container.name, name)
        except LibCloudObjectDoesNotExistError:
            raise ObjectDoesNotExistError
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)
