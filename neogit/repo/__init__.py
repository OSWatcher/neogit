"""This package contains repositories implementing the Repository Architectural Pattern for a graph database"""
from .abstract import AbstractGraphRepository
from .fake import FakeRepository
from .py2neo import Py2NeoRepository
