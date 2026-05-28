# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from dataclasses import asdict
from functools import wraps
from pathlib import Path
from typing import Iterator, Optional

from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container as LibCloudContainer
from libcloud.storage.base import Object as LibCloudObject
from libcloud.storage.drivers.local import LocalStorageDriver
from libcloud.storage.drivers.minio import MinIOStorageDriver
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
    ObjectStorageError,
)


def wraps_exception(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            ret = f(*args, **kwargs)
        except LibCloudContainerAlreadyExistsError as e:
            raise ContainerAlreadyExists from e
        except LibCloudContainerDoesNotExistError as e:
            raise ContainerDoesNotExistError from e
        except LibCloudObjectDoesNotExistError as e:
            raise ObjectDoesNotExistError from e
        # catch all unhandled libcloud errors
        except LibcloudError as e:
            raise ObjectStorageError from e
        # rest just raise standard python errors
        else:
            return ret

    return wrapper


class LibcloudObjectStorage(AbstractObjectStorage):
    def __init__(self, config: ObjectConfig):
        cls = get_driver(config.provider)
        # local provider: ensure directory is created
        if cls == LocalStorageDriver:
            Path(config.key).mkdir(parents=True, exist_ok=True)
        # drop all keys whose values is None
        config_dict = {k: v for k, v in asdict(config).items() if v is not None}
        if cls == MinIOStorageDriver:
            # replace 'secret_key' key name by 'secret' if present
            if "secret_key" in config_dict:
                config_dict["secret"] = config_dict["secret_key"]
                del config_dict["secret_key"]
        if cls == LocalStorageDriver:
            # bug when port value is set
            # just drop everything else except necessary
            config_dict = {"provider": "local", "key": config_dict["key"]}
        # drop provider as well (already used before)
        del config_dict["provider"]
        self._driver = cls(**config_dict)

    @wraps_exception
    def create_container(self, name: str) -> Container:
        try:
            c: LibCloudContainer = self._driver.create_container(name)
        except LibCloudContainerAlreadyExistsError:
            raise ContainerAlreadyExists
        else:
            return Container(c.name)

    @wraps_exception
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

    @wraps_exception
    def iterate_containers(self) -> Iterator[Container]:
        gen_containers = (Container(c.name) for c in self._driver.iterate_containers())
        yield from gen_containers

    @wraps_exception
    def iterate_container_objects(self, container: Container) -> Iterator[Object]:
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        for obj in self._driver.iterate_container_objects(libcloud_container):
            yield Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)

    @wraps_exception
    def get_container(self, name: str) -> Container:
        # Check if container exists first by iterating through containers
        # This prevents auto-creation behavior in newer MinIO versions
        existing_containers = {c.name for c in self._driver.iterate_containers()}
        if name not in existing_containers:
            raise ContainerDoesNotExistError(f"Container '{name}' does not exist")

        c: LibCloudContainer = self._driver.get_container(name)
        return Container(c.name)

    @wraps_exception
    def upload_object(
        self, filepath: str, container: Container, object_name: str, extra: Optional[dict] = None
    ) -> Object:
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        obj: LibCloudObject = self._driver.upload_object(filepath, libcloud_container, object_name, extra, True)
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)

    @wraps_exception
    def upload_object_via_stream(
        self, iterator: Iterator[bytes], container: Container, object_name: str, extra: Optional[dict] = None
    ) -> Object:
        libcloud_container = LibCloudContainer(container.name, {}, self._driver)
        obj: LibCloudObject = self._driver.upload_object_via_stream(iterator, libcloud_container, object_name, extra)
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)

    @wraps_exception
    def download_object(self, obj: Object, destination_path: str, overwrite_existing: bool = False) -> bool:
        libcloud_container = LibCloudContainer(obj.container.name, {}, self._driver)
        libcloud_object = LibCloudObject(
            obj.name, obj.size, obj.hash, obj.extra, obj.meta_data, libcloud_container, self._driver
        )
        return self._driver.download_object(libcloud_object, destination_path, overwrite_existing)

    @wraps_exception
    def download_object_as_stream(self, obj: Object, chunk_size: Optional[int] = None) -> Iterator[bytes]:
        libcloud_container = LibCloudContainer(obj.container.name, {}, self._driver)
        libcloud_object = LibCloudObject(
            obj.name, obj.size, obj.hash, obj.extra, obj.meta_data, libcloud_container, self._driver
        )
        yield from self._driver.download_object_as_stream(libcloud_object, chunk_size)

    @wraps_exception
    def get_object(self, container: Container, name: str) -> Object:
        obj: LibCloudObject = self._driver.get_object(container.name, name)
        return Object(obj.name, obj.size, obj.hash, container, obj.extra, obj.meta_data)

    @wraps_exception
    def delete_object(self, obj: Object) -> bool:
        try:
            libcloud_obj: LibCloudObject = self._driver.get_object(obj.container.name, obj.name)
        except LibCloudObjectDoesNotExistError:
            raise ObjectDoesNotExistError
        else:
            return self._driver.delete_object(libcloud_obj)
