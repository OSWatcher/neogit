from abc import ABC, abstractmethod

from py2neo.ogm import Model


class AbstractGraphRepository(ABC):
    """
    Abstract repository pattern for graph databases
    """

    @abstractmethod
    def delete(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def exists(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def get(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def match(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def reload(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def save(self, *obj: Model):
        raise NotImplementedError
