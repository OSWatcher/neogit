from libcloud.storage.base import Container as LibCloudContainer
from libcloud.storage.base import Object as LibCloudObject
from libcloud.storage.providers import get_driver
from libcloud.storage.types import ContainerAlreadyExistsError as LibCloudContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError as LibCloudContainerDoesNotExistError

from neogit.config import ObjectConfig
from neogit.object_storage.abstract import (AbstractObjectStorage, Container, ContainerAlreadyExists,
                                            ContainerDoesNotExistError, Object)


class LibcloudObjectStorage(AbstractObjectStorage):
    def __init__(self, config: ObjectConfig):
        cls = get_driver(config.provider)
        self._driver = cls(config.key)

    def create_container(self, name: str) -> Container:
        try:
            c: LibCloudContainer = self._driver.create_container(name)
        except LibCloudContainerAlreadyExistsError:
            raise ContainerAlreadyExists
        else:
            return Container(c.name)

    def delete_container(self, container: Container) -> bool:
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        try:
            self._driver.delete_container(libcloud_container)
        except LibCloudContainerDoesNotExistError:
            return False
        else:
            return True

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
