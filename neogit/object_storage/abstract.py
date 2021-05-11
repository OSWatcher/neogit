"""Defines the interface to the Object Storage"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class StorageDriver:
    pass


@dataclass(frozen=True)
class Container:
    name: str


@dataclass
class Object:
    name: str
    size: int
    hash: str
    container: Container
    extra: dict
    meta_data: dict


class ContainerError(Exception):
    pass


class ContainerAlreadyExists(ContainerError):
    pass


class ContainerDoesNotExistError(ContainerError):
    pass


class ObjectError(Exception):
    pass


class ObjectDoesNotExistError(ObjectError):
    pass


class AbstractObjectStorage(ABC):
    @abstractmethod
    def create_container(self, name: str) -> Container:
        pass

    @abstractmethod
    def delete_container(self, container: Container) -> bool:
        pass

    @abstractmethod
    def get_container(self, name: str) -> Container:
        pass

    @abstractmethod
    def iterate_containers(self) -> Iterator[Container]:
        pass

    @abstractmethod
    def upload_object(self, filepath: str, container: Container, object_name: str, extra: dict = None) -> Object:
        pass

    @abstractmethod
    def upload_object_via_stream(
        self, iterator: Iterator[bytes], container: Container, object_name: str, extra: dict = None
    ) -> Object:
        pass

    @abstractmethod
    def download_object(self, obj: Object, destination_path: str, overwrite_existing: bool = False) -> bool:
        pass

    @abstractmethod
    def get_object(self, container: Container, name: str) -> Object:
        pass
