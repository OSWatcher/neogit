from py2neo.ogm import Model

from .abstract import AbstractGraphRepository


class FakeRepository(AbstractGraphRepository):
    def __init__(self, url: str):
        pass

    def delete(self, obj: Model):
        pass

    def exists(self, obj: Model):
        pass

    def get(self, obj: Model):
        pass

    def match(self, obj: Model):
        pass

    def reload(self, obj: Model):
        pass

    def save(self, *obj: Model):
        pass
