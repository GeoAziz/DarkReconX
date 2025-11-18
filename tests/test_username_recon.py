import pytest

from modules.username_recon.scanner import UsernameRecon


def test_username_recon_search_raises():
    u = UsernameRecon()
    with pytest.raises(NotImplementedError):
        u.search("testuser")
