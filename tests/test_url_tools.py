"""Tests for proxy_string.url_tools module."""

import pytest
from proxy_string.enums import ProxyServerProtocol
from proxy_string.url_tools import (
    build_url,
    get_protocol,
    get_scheme,
    quote_all,
    unquote_all,
)


@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ("simple", "simple"),
        ("12345", "12345"),
        ("user:pass", "user%3Apass"),
        ("a@b:c/d", "a%40b%3Ac%2Fd"),
        ("вася", "%D0%B2%D0%B0%D1%81%D1%8F"),
        (
            "!#$%&'()*+,/:;=?@[]",
            "%21%23%24%25%26%27%28%29%2A%2B%2C%2F%3A%3B%3D%3F%40%5B%5D",
        ),
    ],
)
def test_quote_all_various_inputs_encoded_properly(
    input_str: str, expected: str
) -> None:
    assert quote_all(input_str) == expected


@pytest.mark.parametrize(
    ("encoded_str", "expected"),
    [
        ("simple", "simple"),
        ("user%3Apass", "user:pass"),
        ("%D0%B2%D0%B0%D1%81%D1%8F", "вася"),
    ],
)
def test_unquote_all_encoded_inputs_decoded_properly(
    encoded_str: str, expected: str
) -> None:
    assert unquote_all(encoded_str) == expected


@pytest.mark.parametrize(
    ("scheme", "host", "port", "username", "password", "expected"),
    [
        ("http", "example.com", 8080, None, None, "http://example.com:8080"),
        ("https", "example.com", 443, "user", None, "https://user@example.com:443"),
        ("http", "example.com", 80, None, "secret", "http://:secret@example.com:80"),
        (
            "socks5",
            "example.com",
            1080,
            "user",
            "secret",
            "socks5://user:secret@example.com:1080",
        ),
        (
            "socks5",
            "вася.рф",
            1080,
            "пользователь",
            "пароль",
            "socks5://%D0%BF%D0%BE%D0%BB%D1%8C%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C:%D0%BF%D0%B0%D1%80%D0%BE%D0%BB%D1%8C@вася.рф:1080",
        ),
        ("http", "2001:db8::1", 8080, None, None, "http://[2001:db8::1]:8080"),
        ("http", "[2001:db8::1]", 8080, None, None, "http://[2001:db8::1]:8080"),
    ],
)
def test_build_url_various_combinations_constructed_correctly(
    scheme: str,
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    expected: str,
) -> None:
    assert (
        build_url(scheme, host, port, username=username, password=password) == expected
    )


@pytest.mark.parametrize(
    ("protocol", "remote_dns", "socks_ext", "expected"),
    [
        (ProxyServerProtocol.HTTP, None, True, "http"),
        (ProxyServerProtocol.HTTPS, False, True, "https"),
        (ProxyServerProtocol.SOCKS4, True, True, "socks4a"),
        (ProxyServerProtocol.SOCKS4, True, False, "socks4"),
        (ProxyServerProtocol.SOCKS4, False, True, "socks4"),
        (ProxyServerProtocol.SOCKS4, None, True, "socks4"),
        (ProxyServerProtocol.SOCKS5, True, True, "socks5h"),
        (ProxyServerProtocol.SOCKS5, True, False, "socks5"),
        (ProxyServerProtocol.SOCKS5, False, True, "socks5"),
        (ProxyServerProtocol.SOCKS5, None, True, "socks5"),
        ("SOCKS5", True, True, "socks5h"),
        ("HTTP", False, True, "http"),
    ],
)
def test_get_scheme_various_inputs_resolved_correctly(
    protocol: ProxyServerProtocol | str,
    remote_dns: bool | None,
    socks_ext: bool,
    expected: str,
) -> None:
    assert get_scheme(protocol, remote_dns=remote_dns, socks_ext=socks_ext) == expected


@pytest.mark.parametrize(
    ("scheme", "expected_protocol", "expected_remote_dns"),
    [
        ("socks5h", ProxyServerProtocol.SOCKS5, True),
        ("socks4a", ProxyServerProtocol.SOCKS4, True),
        ("socks5", ProxyServerProtocol.SOCKS5, None),
        ("socks4", ProxyServerProtocol.SOCKS4, None),
        ("http", ProxyServerProtocol.HTTP, False),
        ("https", ProxyServerProtocol.HTTPS, False),
        ("SOCKS5H", ProxyServerProtocol.SOCKS5, True),
        ("HTTP", ProxyServerProtocol.HTTP, False),
    ],
)
def test_get_protocol_various_schemes_parsed_correctly(
    scheme: str,
    expected_protocol: ProxyServerProtocol,
    expected_remote_dns: bool | None,
) -> None:
    proto, remote = get_protocol(scheme)
    assert proto == expected_protocol
    assert remote == expected_remote_dns


def test_get_protocol_invalid_scheme_raises_value_error() -> None:
    """Tests that an unsupported scheme raises ValueError in get_protocol."""
    with pytest.raises(ValueError):
        get_protocol("ftp")
