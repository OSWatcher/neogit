from unittest.mock import patch

import pytest

from neogit import DEFAULT_NEO4J_URI, Neogit


def test_init_url_not_string_should_raise_typeerror():
    with pytest.raises(TypeError):
        Neogit(url=4)


def test_init_auth_not_tuple_should_raise_typeerror():
    with pytest.raises(TypeError):
        Neogit(auth="26")


@patch("neogit.neogit.GraphDatabase", autospec=True)
def test_init_default_uri(mock_db):
    Neogit()
    mock_db.driver.assert_called_once_with(DEFAULT_NEO4J_URI, auth=None)


@patch("neogit.neogit.GraphDatabase", autospec=True)
def test_init_uri(mock_db):
    uri = "my_uri"
    Neogit(uri)
    mock_db.driver.assert_called_once_with(uri, auth=None)


@patch("neogit.neogit.GraphDatabase", autospec=True)
def test_init_auth(mock_db):
    auth = ("user", "user")
    Neogit(auth=auth)
    mock_db.driver.assert_called_once()
    assert auth == mock_db.driver.call_args.kwargs["auth"]
