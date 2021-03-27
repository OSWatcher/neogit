from neogit.merkle.utils import compute_sha1
from tests.conftest import TEST_DATA
import pytest

TEST_DATA_SHA = TEST_DATA / "sha1"


@pytest.mark.parametrize(
    "filename,expected_sha1",
    [
        ("1024.raw", "4625996e17e4c1acbfc1db9044e124097b8d8cb0"),
        ("4096.raw", "1b07c94f6664bd7cc40948716ecb9ba4baca430f"),
        ("64k.raw", "0fb500a2b6ff43385ea59a7d4d7ca7ad78797a67"),
        ("63k.raw", "0d1e8f5fd8735aa901dccecdcd4663b9a84c735b"),
    ],
)
def test_compute_sha1(filename, expected_sha1):
    filepath = TEST_DATA_SHA / filename
    sha1 = compute_sha1(filepath)
    assert expected_sha1, sha1
