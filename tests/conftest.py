"""Pytest session and test fixtures for proxy-server-parser."""

from pathlib import Path

import pytest
from proxy_string import ProxyServer


@pytest.fixture(scope="session")
def proxy_server_class() -> type[ProxyServer]:
    """Returns the ProxyServer class for session-scoped usage.

    Returns:
        type[ProxyServer]: The ProxyServer class.
    """
    return ProxyServer


@pytest.fixture
def temp_proxy_file(tmp_path: Path) -> Path:
    """Creates a temporary text file with valid proxy string rows and comments.

    Args:
        tmp_path: pytest tmp_path fixture.

    Returns:
        Path: Path to the generated file.
    """
    file_path = tmp_path / "proxies.txt"
    content = (
        "# List of proxy servers\n"
        "http://proxy1.com:8080\n"
        "\n"
        "socks5://user:pass@127.0.0.1:1080\n"
        "192.168.1.100:3128\n"
        "admin:secret@proxy2.org:8000\n"
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def temp_proxy_file_with_invalid_rows(tmp_path: Path) -> Path:
    """Creates a temporary text file containing both valid and invalid rows.

    Args:
        tmp_path: pytest tmp_path fixture.

    Returns:
        Path: Path to the generated file.
    """
    file_path = tmp_path / "proxies_with_invalid.txt"
    content = "http://proxy1.com:8080\ninvalid_proxy_without_port\n192.168.1.100:3128\n"
    file_path.write_text(content, encoding="utf-8")
    return file_path
