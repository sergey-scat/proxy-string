"""Unit tests for the ProxyServer base class."""

import json
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Any

import pytest
from attrs.exceptions import FrozenInstanceError
from proxy_string import (
    HostValueType,
    InvalidProxyStringError,
    InvalidProxyURLError,
    ProtocolConstraintError,
    ProtocolNotSupportedError,
    ProxyConfigurationError,
    ProxyServer,
    ProxyServerProtocol,
    ProxyStringFormat,
    UnsupportedPackageError,
)

SCHEMES = ("http", "https", "socks4", "socks5", "socks4a", "socks5h")
PROTOCOL_BY_SCHEME = {
    "http": ProxyServerProtocol.HTTP,
    "https": ProxyServerProtocol.HTTPS,
    "socks4": ProxyServerProtocol.SOCKS4,
    "socks5": ProxyServerProtocol.SOCKS5,
    "socks4a": ProxyServerProtocol.SOCKS4,
    "socks5h": ProxyServerProtocol.SOCKS5,
}
PORT_BY_PROTO = {"http": 80, "https": 443, "socks4": 1080, "socks5": 1080}


@pytest.mark.parametrize("scheme", SCHEMES)
def test_init_with_all_params_sets_attributes_correctly(
    scheme: str,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests ProxyServer initialization with all parameters specified."""
    expected_remote_dns = scheme in ("socks4a", "socks5h")
    proxy_server = proxy_server_class(
        host="test123.com",
        port=12345,
        protocol=scheme,
        username="user1",
        password="pass1",
        remote_dns=expected_remote_dns,
    )
    assert proxy_server.host == "test123.com"
    assert proxy_server.protocol is PROTOCOL_BY_SCHEME[scheme]
    assert proxy_server.port == 12345
    assert proxy_server.username == "user1"
    assert proxy_server.password == "pass1"
    assert proxy_server.unicode_host == "test123.com"
    assert proxy_server.remote_dns is expected_remote_dns


def test_init_with_host_only_sets_defaults(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests initialization when providing only the host."""
    proxy_server = proxy_server_class(host="test123.com")
    assert proxy_server.host == "test123.com"
    assert proxy_server.protocol is ProxyServerProtocol.HTTP
    assert proxy_server.port == PORT_BY_PROTO[ProxyServerProtocol.HTTP]
    assert proxy_server.username is None
    assert proxy_server.password is None
    assert proxy_server.unicode_host == "test123.com"
    assert proxy_server.remote_dns is False


@pytest.mark.parametrize("scheme", SCHEMES)
def test_init_for_default_port_resolves_expected_port(
    scheme: str,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests default port resolution for all supported schemes."""
    proxy_server = proxy_server_class(host="test123.com", protocol=scheme)

    expected_proto = PROTOCOL_BY_SCHEME[scheme]
    if scheme in ("http", "https"):
        expected_remote_dns = False
    elif scheme in ("socks4a", "socks5h"):
        expected_remote_dns = True
    else:
        expected_remote_dns = None

    assert proxy_server.host == "test123.com"
    assert proxy_server.protocol is expected_proto
    assert proxy_server.port == PORT_BY_PROTO[expected_proto]
    assert proxy_server.username is None
    assert proxy_server.password is None
    assert proxy_server.remote_dns is expected_remote_dns


def test_init_unicode_host_converts_properly(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests initialization with an IDN Unicode host."""
    proxy_server = proxy_server_class(host="прокси.рф", protocol="http")
    assert proxy_server.unicode_host == "прокси.рф"
    assert proxy_server.host == "xn--h1adldfi.xn--p1ai"


def test_init_unicode_credentials_supported_properly(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests initialization with Unicode username and password."""
    proxy = proxy_server_class(
        host="example.com",
        username="юзер_вася",
        password="пароль_секрет",
    )
    assert proxy.username == "юзер_вася"
    assert proxy.password == "пароль_секрет"
    assert "%D1%8E%D0%B7%D0%B5%D1%80" in proxy.to_url()


def test_init_socks4_with_ipv6_host_raises_protocol_constraint_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests initializing SOCKS4 with IPv6 host raises ProtocolConstraintError."""
    with pytest.raises(
        ProtocolConstraintError, match="SOCKS4 protocol does not support IPv6 addresses"
    ):
        proxy_server_class(host="2001:db8::1", protocol="socks4")


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_init_http_with_remote_dns_true_raises_protocol_constraint_error(
    scheme: str,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that HTTP and HTTPS reject remote_dns=True during initialization."""
    with pytest.raises(
        ProtocolConstraintError, match="protocol does not support remote DNS resolution"
    ):
        proxy_server_class(host="example.com", protocol=scheme, remote_dns=True)


@pytest.mark.parametrize("scheme", ["socks4a", "socks5h"])
def test_init_socks_ext_with_remote_dns_false_raises_protocol_constraint_error(
    scheme: str,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that socks4a/socks5h reject remote_dns=False during initialization."""
    with pytest.raises(ProtocolConstraintError, match="Conflicting configuration"):
        proxy_server_class(host="example.com", protocol=scheme, remote_dns=False)


@pytest.mark.parametrize("invalid_port", [-1, 65536, 100000])
def test_init_invalid_port_range_raises_validation_error(
    invalid_port: int,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that port validator rejects ports outside 0-65535."""
    with pytest.raises(ValueError):
        proxy_server_class(host="example.com", port=invalid_port)


def test_init_empty_host_raises_validation_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that an empty host string fails min_len(1) validation."""
    with pytest.raises(ValueError):
        proxy_server_class(host="")


def test_init_port_zero_replaces_with_default_protocol_port(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that port 0 is replaced by protocol default port during initialization."""
    proxy = proxy_server_class(host="example.com", port=0, protocol="http")
    assert proxy.port == 80


def test_proxy_server_frozen_immutability_raises_frozen_instance_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that attributes cannot be modified on a frozen ProxyServer instance."""
    proxy = proxy_server_class(host="example.com")
    with pytest.raises(FrozenInstanceError):
        proxy.port = 8080  # type: ignore[misc]


def test_proxy_server_equality_and_hash_consistency(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests two instances with equal attributes have identical equality and hashes."""
    proxy1 = proxy_server_class(host="proxy.com", port=8080, protocol="http")
    proxy2 = proxy_server_class(host="proxy.com", port=8080, protocol="http")
    assert proxy1 == proxy2
    assert hash(proxy1) == hash(proxy2)
    assert len({proxy1, proxy2}) == 1


def test_proxy_server_equality_different_attributes_not_equal(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests differing instances are not equal and have distinct hashes."""
    proxy1 = proxy_server_class(
        host="proxy.com", port=1080, protocol="socks5", remote_dns=True
    )
    proxy2 = proxy_server_class(
        host="proxy.com", port=1080, protocol="socks5", remote_dns=False
    )
    assert proxy1 != proxy2
    assert hash(proxy1) != hash(proxy2)
    assert len({proxy1, proxy2}) == 2


@pytest.mark.parametrize(
    ("proxy_str", "fmt", "expected"),
    [
        (
            "proxy.com:8080",
            ProxyStringFormat.HOST_PORT,
            {"host": "proxy.com", "port": 8080, "user": None, "pass": None},
        ),
        (
            "user:pass:proxy.com:3128",
            ProxyStringFormat.USER_PASS_HOST_PORT,
            {"host": "proxy.com", "port": 3128, "user": "user", "pass": "pass"},
        ),
        (
            "user:pass@proxy.com:3128",
            ProxyStringFormat.USER_PASS_AT_HOST_PORT,
            {"host": "proxy.com", "port": 3128, "user": "user", "pass": "pass"},
        ),
        (
            "proxy.com:3128:user:pass",
            ProxyStringFormat.HOST_PORT_USER_PASS,
            {"host": "proxy.com", "port": 3128, "user": "user", "pass": "pass"},
        ),
        (
            "proxy.com:3128@user:pass",
            ProxyStringFormat.HOST_PORT_AT_USER_PASS,
            {"host": "proxy.com", "port": 3128, "user": "user", "pass": "pass"},
        ),
    ],
)
def test_from_string_all_formats_creates_proxy_server(
    proxy_str: str,
    fmt: ProxyStringFormat,
    expected: dict[str, Any],
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests ProxyServer.from_string across all supported ProxyStringFormat options."""
    proxy = proxy_server_class.from_string(proxy_str, string_format=fmt)
    assert proxy.host == expected["host"]
    assert proxy.port == expected["port"]
    assert proxy.username == expected["user"]
    assert proxy.password == expected["pass"]


def test_from_string_with_protocol_override(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_string applies explicit protocol parameter override."""
    proxy = proxy_server_class.from_string(
        "proxy.com:8080", protocol=ProxyServerProtocol.SOCKS5
    )
    assert proxy.protocol is ProxyServerProtocol.SOCKS5


def test_from_string_without_protocol_defaults_to_http(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_string defaults to HTTP protocol when none is specified."""
    proxy = proxy_server_class.from_string("proxy.com:8080")
    assert proxy.protocol is ProxyServerProtocol.HTTP


def test_from_string_with_scheme_in_url_format(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_string derives protocol from scheme if present in URL string."""
    proxy = proxy_server_class.from_string("socks5://user:pass@127.0.0.1:1080")
    assert proxy.protocol is ProxyServerProtocol.SOCKS5
    assert proxy.host == "127.0.0.1"


def test_from_string_invalid_format_raises_invalid_proxy_string_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that invalid proxy string raises InvalidProxyStringError."""
    with pytest.raises(
        InvalidProxyStringError, match="Unable to parse the proxy string"
    ):
        proxy_server_class.from_string("not_a_valid_proxy")


def test_from_string_with_padded_whitespace_parses_successfully(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests ProxyServer.from_string strips leading and trailing whitespace."""
    proxy = proxy_server_class.from_string("   user:pass@1.2.3.4:8080   ")
    assert proxy.host == "1.2.3.4"
    assert proxy.port == 8080
    assert proxy.username == "user"
    assert proxy.password == "pass"


def test_from_url_creates_proxy_server(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests creating ProxyServer using from_url."""
    proxy = proxy_server_class.from_url("http://user:pass@example.com:8080")
    assert proxy.host == "example.com"
    assert proxy.port == 8080
    assert proxy.username == "user"
    assert proxy.password == "pass"
    assert proxy.protocol == ProxyServerProtocol.HTTP


def test_from_dict_and_from_json_creates_proxy_server(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests creating ProxyServer from dictionary and JSON."""
    data = {
        "host": "proxy.com",
        "port": 3128,
        "protocol": "https",
        "username": "user",
        "password": "pass",
    }
    proxy_dict = proxy_server_class.from_dict(data)
    assert proxy_dict.host == "proxy.com"
    assert proxy_dict.port == 3128

    json_str = json.dumps(data)
    proxy_json = proxy_server_class.from_json(json_str)
    assert proxy_json == proxy_dict


def test_from_dict_with_extended_scheme(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_dict creates ProxyServer using scheme key with extended SOCKS."""
    proxy = proxy_server_class.from_dict({"host": "proxy.com", "scheme": "socks5h"})
    assert proxy.protocol is ProxyServerProtocol.SOCKS5
    assert proxy.remote_dns is True
    assert proxy.port == 1080


def test_from_dict_omitted_port_uses_protocol_default(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_dict resolves default port by protocol when port is omitted."""
    proxy_without_port = proxy_server_class.from_dict(
        {"host": "proxy.com", "protocol": "socks5"}
    )
    assert proxy_without_port.port == 1080

    proxy_none_port = proxy_server_class.from_dict(
        {"host": "proxy.com", "scheme": "https", "port": None}
    )
    assert proxy_none_port.port == 443


def test_from_file_valid_rows_yields_proxy_servers(
    temp_proxy_file: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file yields all valid ProxyServer instances from a text file."""
    proxies = list(proxy_server_class.from_file(temp_proxy_file))
    assert len(proxies) == 4
    assert proxies[0].host == "proxy1.com"
    assert proxies[1].protocol is ProxyServerProtocol.SOCKS5


def test_from_file_invalid_rows_strict_mode_raises_invalid_proxy_string_error(
    temp_proxy_file_with_invalid_rows: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file raises InvalidProxyStringError in strict mode on invalid row."""
    with pytest.raises(InvalidProxyStringError):
        list(
            proxy_server_class.from_file(
                temp_proxy_file_with_invalid_rows, ignore_invalid=False
            )
        )


def test_from_file_invalid_rows_ignore_mode_skips_errors(
    temp_proxy_file_with_invalid_rows: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file skips invalid rows when ignore_invalid=True is specified."""
    proxies = list(
        proxy_server_class.from_file(
            temp_proxy_file_with_invalid_rows, ignore_invalid=True
        )
    )
    assert len(proxies) == 2


@pytest.mark.asyncio
async def test_from_file_async_valid_rows_yields_proxy_servers(
    temp_proxy_file: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file_async asynchronously yields ProxyServer instances from file."""
    proxies = [p async for p in proxy_server_class.from_file_async(temp_proxy_file)]
    assert len(proxies) == 4


@pytest.mark.asyncio
async def test_from_file_async_invalid_rows_strict_raises_invalid_proxy_string_error(
    temp_proxy_file_with_invalid_rows: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file_async raises InvalidProxyStringError on invalid rows strictly."""
    with pytest.raises(InvalidProxyStringError):
        async for _ in proxy_server_class.from_file_async(
            temp_proxy_file_with_invalid_rows, ignore_invalid=False
        ):
            pass


@pytest.mark.asyncio
async def test_from_file_async_invalid_rows_ignore_mode_skips_errors(
    temp_proxy_file_with_invalid_rows: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file_async skips invalid rows when ignore_invalid=True."""
    proxies = [
        p
        async for p in proxy_server_class.from_file_async(
            temp_proxy_file_with_invalid_rows, ignore_invalid=True
        )
    ]
    assert len(proxies) == 2


@pytest.mark.parametrize(
    ("string_format", "expected_str"),
    [
        (ProxyStringFormat.HOST_PORT, "proxy.com:8080"),
        (ProxyStringFormat.USER_PASS_HOST_PORT, "user:pass:proxy.com:8080"),
        (ProxyStringFormat.USER_PASS_AT_HOST_PORT, "user:pass@proxy.com:8080"),
        (ProxyStringFormat.HOST_PORT_USER_PASS, "proxy.com:8080:user:pass"),
        (ProxyStringFormat.HOST_PORT_AT_USER_PASS, "proxy.com:8080@user:pass"),
        (ProxyStringFormat.URL, "http://user:pass@proxy.com:8080"),
    ],
)
def test_to_string_all_formats_returns_formatted_string(
    string_format: ProxyStringFormat,
    expected_str: str,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that to_string returns directly formatted string for all formats."""
    proxy = proxy_server_class(
        host="proxy.com", port=8080, username="user", password="pass"
    )
    result = proxy.to_string(string_format)
    assert isinstance(result, str)
    assert result == expected_str


def test_to_string_format_none_with_credentials_returns_host_port_user_pass(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests to_string defaults to HOST_PORT_USER_PASS when credentials are present."""
    proxy = proxy_server_class(
        host="proxy.com", port=8080, username="user", password="pass"
    )
    s = proxy.to_string()
    assert s == "proxy.com:8080:user:pass"


def test_to_string_format_none_without_credentials_returns_host_port(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that to_string defaults to HOST_PORT when no credentials are present."""
    proxy = proxy_server_class(host="proxy.com", port=8080)
    s = proxy.to_string()
    assert s == "proxy.com:8080"


def test_to_url_options(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests to_url options: exclude_credentials and socks_ext."""
    proxy = proxy_server_class(
        host="proxy.com",
        port=8080,
        username="user",
        password="pass",
        protocol="socks5h",
    )
    assert proxy.to_url(exclude_credentials=True) == "socks5h://proxy.com:8080"
    assert proxy.to_url(socks_ext=False) == "socks5://user:pass@proxy.com:8080"
    assert proxy.to_url(socks_ext=True) == "socks5h://user:pass@proxy.com:8080"


def test_properties_and_dunder_methods(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests properties url, origin, unicode_url, host_ip_address, and __str__."""
    proxy = proxy_server_class(
        host="прокси.рф",
        port=8080,
        username="user",
        password="pass",
    )
    assert proxy.url == proxy.to_url()
    assert proxy.origin == "http://xn--h1adldfi.xn--p1ai:8080"
    assert "прокси.рф" in proxy.unicode_url
    assert proxy.host_ip_address is None
    assert str(proxy) == proxy.to_url()
    assert "ProxyServer(" in repr(proxy)
    assert "***" in repr(proxy)

    proxy_ip4 = proxy_server_class(host="192.168.1.1", port=8080)
    assert proxy_ip4.host_ip_address == IPv4Address("192.168.1.1")

    proxy_ip6 = proxy_server_class(host="2001:db8::1", port=8080)
    assert proxy_ip6.host_ip_address == IPv6Address("2001:db8::1")


def test_to_dict_and_to_json(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests to_dict and to_json serialization."""
    proxy = proxy_server_class(
        host="proxy.com", port=8080, username="user", password="secret"
    )
    d = proxy.to_dict()
    assert d["host"] == "proxy.com"
    assert d["port"] == 8080
    assert d["username"] == "user"
    assert d["password"] == "secret"

    j = json.loads(proxy.to_json())
    assert j == d


def test_with_methods_evolve_instance(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests with_* evolution methods."""
    proxy = proxy_server_class(host="proxy.com", port=8080)

    p_host = proxy.with_host("other.com")
    assert p_host.host == "other.com"

    p_port = proxy.with_port(9090)
    assert p_port.port == 9090

    p_proto = proxy.with_protocol(ProxyServerProtocol.HTTPS)
    assert p_proto.protocol == ProxyServerProtocol.HTTPS

    p_user = proxy.with_username("alice")
    assert p_user.username == "alice"

    p_pass = proxy.with_password("secret")
    assert p_pass.password == "secret"

    p_creds = proxy.with_creds("bob", "pass123")
    assert p_creds.username == "bob"
    assert p_creds.password == "pass123"

    p_dns = proxy.with_protocol(ProxyServerProtocol.SOCKS5).with_remote_dns(True)
    assert p_dns.remote_dns is True


@pytest.mark.parametrize(
    ("pkg", "expected_type"),
    [
        ("urllib", dict),
        ("requests", dict),
        ("urllib3", str),
        ("httpx", str),
        ("httpx2", str),
        ("aiohttp", str),
        ("playwright", dict),
        ("pycurl", str),
        ("curl_cffi", str),
    ],
)
def test_prepare_for_supported_packages(
    pkg: str,
    expected_type: type,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests prepare_for across all supported third-party HTTP clients."""
    proxy = proxy_server_class(
        host="proxy.com", port=8080, username="user", password="pass"
    )
    result = proxy.prepare_for(pkg)
    assert isinstance(result, expected_type)


def test_prepare_for_unsupported_package_raises_unsupported_package_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests prepare_for with unsupported package raises UnsupportedPackageError."""
    proxy = proxy_server_class(host="proxy.com", port=8080)
    with pytest.raises(
        UnsupportedPackageError, match="Package 'unknown_pkg' is not supported"
    ):
        proxy.prepare_for("unknown_pkg")  # type: ignore[arg-type]


def test_prepare_for_unsupported_protocol_raises_protocol_not_supported_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests unsupported protocol for client raises ProtocolNotSupportedError."""
    proxy = proxy_server_class(host="proxy.com", port=1080, protocol="socks5")
    with pytest.raises(
        ProtocolNotSupportedError, match="does not support the 'socks5' protocol"
    ):
        proxy.prepare_for("urllib")


def test_init_skip_validation_without_host_value_type_raises_proxy_configuration_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that _skip_validation=True requires _host_value_type to be specified."""
    with pytest.raises(
        ProxyConfigurationError,
        match=(
            "The 'host_value_type' parameter must be specified "
            "when validation is skipped"
        ),
    ):
        proxy_server_class(
            host="1.2.3.4",
            port=8080,
            skip_validation=True,
            host_value_type=None,
        )


def test_unicode_host_with_ip_address_returns_raw_host(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests unicode_host returns the raw host string when host is an IP address."""
    proxy = proxy_server_class(host="192.168.1.1", port=8080)
    assert proxy.unicode_host == "192.168.1.1"


def test_from_string_with_string_format_and_protocol_override(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_string applies protocol override when explicit format is provided."""
    proxy = proxy_server_class.from_string(
        "1.2.3.4:8080",
        string_format=ProxyStringFormat.HOST_PORT,
        protocol=ProxyServerProtocol.SOCKS5,
    )
    assert proxy.protocol is ProxyServerProtocol.SOCKS5
    assert proxy.host == "1.2.3.4"
    assert proxy.port == 8080


def test_from_string_with_protocol_override_does_not_pollute_parse_url_cache(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_string with protocol override does not corrupt parse_url cache."""
    url = "http://cache-test-proxy.com:8080"
    p1 = proxy_server_class.from_string(url, protocol=ProxyServerProtocol.SOCKS5)
    assert p1.protocol is ProxyServerProtocol.SOCKS5

    p2 = proxy_server_class.from_url(url)
    assert p2.protocol is ProxyServerProtocol.HTTP


def test_with_host_evolved_from_url_updates_host_type(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests with_host on from_url re-validates and updates host classification."""
    p_ip = proxy_server_class.from_url("http://1.2.3.4:8080")
    assert p_ip.host_ip_address == IPv4Address("1.2.3.4")

    p_host = p_ip.with_host("example.com")
    assert p_host.host == "example.com"
    assert p_host.host_ip_address is None

    p_ip6 = p_host.with_host("2001:db8::1")
    assert p_ip6.host == "2001:db8::1"
    assert p_ip6.host_ip_address == IPv6Address("2001:db8::1")


def test_with_protocol_evolved_from_url_enforces_protocol_restrictions(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests with_protocol on from_url re-validates protocol restrictions."""
    p_ip6 = proxy_server_class.from_url("http://[2001:db8::1]:8080")
    with pytest.raises(
        ProtocolConstraintError, match="SOCKS4 protocol does not support IPv6 addresses"
    ):
        p_ip6.with_protocol(ProxyServerProtocol.SOCKS4)


def test_with_remote_dns_evolved_from_url_enforces_protocol_restrictions(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests with_remote_dns on from_url re-validates remote_dns restrictions."""
    p_http = proxy_server_class.from_url("http://1.2.3.4:8080")
    with pytest.raises(
        ProtocolConstraintError,
        match="HTTP protocol does not support remote DNS resolution",
    ):
        p_http.with_remote_dns(True)

    p_socks = proxy_server_class.from_url("socks5h://1.2.3.4:1080")
    assert p_socks.remote_dns is True
    p_socks_reset = p_socks.with_remote_dns(None)
    assert p_socks_reset.remote_dns is None


def test_from_json_with_extended_scheme_creates_proxy_server(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_json supports scheme key identically to from_dict."""
    json_str = json.dumps({"host": "proxy.com", "scheme": "socks5h"})
    proxy = proxy_server_class.from_json(json_str)
    assert proxy.protocol is ProxyServerProtocol.SOCKS5
    assert proxy.remote_dns is True
    assert proxy.port == 1080


def test_from_json_omitted_or_none_port_uses_protocol_default(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_json handles null port using protocol default."""
    json_str = json.dumps({"host": "proxy.com", "scheme": "https", "port": None})
    proxy = proxy_server_class.from_json(json_str)
    assert proxy.port == 443


def test_from_dict_non_mapping_input_raises_type_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_dict raises TypeError when input is not a mapping."""
    with pytest.raises(TypeError, match="Input data must be a dictionary or mapping!"):
        proxy_server_class.from_dict("not_a_mapping")  # type: ignore[arg-type]


def test_from_json_non_mapping_input_raises_type_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that from_json raises TypeError when deserialized JSON is not a mapping."""
    with pytest.raises(TypeError, match="Input data must be a dictionary or mapping!"):
        proxy_server_class.from_json("123")


def test_proxy_string_exceptions_inheritance_hierarchy() -> None:
    """Tests that all custom exceptions inherit from ProxyStringError."""
    from proxy_string import (
        InvalidProxyStringError,
        InvalidProxyURLError,
        ProtocolConstraintError,
        ProtocolNotSupportedError,
        ProxyConfigurationError,
        ProxyStringError,
        UnsupportedPackageError,
    )

    assert issubclass(ProxyStringError, Exception)
    assert issubclass(InvalidProxyStringError, ProxyStringError)
    assert issubclass(InvalidProxyURLError, ProxyStringError)
    assert issubclass(ProxyConfigurationError, ProxyStringError)
    assert issubclass(ProtocolConstraintError, ProxyConfigurationError)
    assert issubclass(UnsupportedPackageError, ProxyConfigurationError)
    assert issubclass(ProtocolNotSupportedError, ProxyConfigurationError)


@pytest.mark.parametrize(
    ("proto", "expected_port"),
    [
        (ProxyServerProtocol.HTTPS, 80),
        (ProxyServerProtocol.SOCKS4, 80),
        (ProxyServerProtocol.SOCKS5, 80),
    ],
)
def test_init_explicit_port_eighty_preserved_for_non_http_protocols(
    proto: ProxyServerProtocol,
    expected_port: int,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that initializing non-HTTP protocols on port 80 preserves port 80."""
    proxy = proxy_server_class(host="example.com", port=80, protocol=proto)
    assert proxy.port == expected_port


def test_from_string_protocol_override_socks4_ipv6_raises_protocol_constraint_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests overriding protocol to SOCKS4 on IPv6 URL re-validates and raises error."""
    with pytest.raises(
        ProtocolConstraintError, match="SOCKS4 protocol does not support IPv6 addresses"
    ):
        proxy_server_class.from_string(
            "socks5://[2001:db8::1]:1080",
            string_format=ProxyStringFormat.URL,
            protocol=ProxyServerProtocol.SOCKS4,
        )


def test_from_string_protocol_override_socks4_ipv6_auto_detect_raises_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests overriding protocol to SOCKS4 on IPv6 with auto-detection raises error."""
    with pytest.raises(InvalidProxyStringError):
        proxy_server_class.from_string(
            "socks5://[2001:db8::1]:1080",
            protocol=ProxyServerProtocol.SOCKS4,
        )


def test_from_string_override_http_remote_dns_raises_protocol_constraint_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests overriding protocol to HTTP on remote DNS URL raises error."""
    with pytest.raises(
        ProtocolConstraintError,
        match="HTTP protocol does not support remote DNS resolution",
    ):
        proxy_server_class.from_string(
            "socks5h://1.2.3.4:1080",
            string_format=ProxyStringFormat.URL,
            protocol=ProxyServerProtocol.HTTP,
        )


@pytest.mark.parametrize(
    ("host", "expected_type"),
    [
        ("example.com", HostValueType.HOSTNAME),
        ("1.2.3.4", HostValueType.IPV4),
        ("2001:db8::1", HostValueType.IPV6),
    ],
)
def test_host_value_type_property_returns_expected_classification(
    host: str,
    expected_type: HostValueType,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests host_value_type property accurately returns HostValueType enum member."""
    proxy = proxy_server_class(host=host, port=8080)
    assert proxy.host_value_type is expected_type


def test_init_with_empty_password_preserves_empty_string(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that explicit empty string password is preserved and roundtrips via URL."""
    proxy = proxy_server_class(
        host="example.com", port=8080, username="user", password=""
    )
    assert proxy.password == ""
    assert proxy.url == "http://user:@example.com:8080"
    p2 = proxy_server_class.from_url(proxy.url)
    assert p2.password == ""
    s = proxy.to_string()
    assert s == "example.com:8080:user:"
    p3 = proxy_server_class.from_string(s)
    assert p3.password == ""


@pytest.mark.parametrize(
    "pkg_name",
    ["Requests", "requests", " REQUESTS ", "  Playwright  ", "Httpx"],
)
def test_prepare_for_package_name_is_case_insensitive(
    pkg_name: str,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests prepare_for accepts package names in any casing and with spaces."""
    proxy = proxy_server_class(host="example.com", port=8080)
    res = proxy.prepare_for(pkg_name)
    assert res is not None


def test_from_file_encoding_errors_strict_raises_unicode_decode_error(
    tmp_path: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests encoding_errors='strict' raises UnicodeDecodeError when reading."""
    bad_file = tmp_path / "bad_utf8.txt"
    bad_file.write_bytes(b"http://proxy.com:8080\n\xff\xfe\nhttp://proxy2.com:8080\n")
    with pytest.raises(UnicodeDecodeError):
        list(
            proxy_server_class.from_file(
                bad_file, ignore_invalid=True, encoding_errors="strict"
            )
        )


def test_from_file_encoding_errors_ignore_skips_bad_bytes(
    tmp_path: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests encoding_errors='ignore' ignores byte decoding errors in file."""
    bad_file = tmp_path / "bad_utf8.txt"
    bad_file.write_bytes(b"http://proxy.com:8080\nhttp://proxy2.com:8080\n")
    proxies = list(proxy_server_class.from_file(bad_file, encoding_errors="ignore"))
    assert len(proxies) == 2


@pytest.mark.asyncio
async def test_from_file_async_encoding_errors_strict_raises_unicode_decode_error(
    tmp_path: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests from_file_async with encoding_errors='strict' raises UnicodeDecodeError."""
    bad_file = tmp_path / "bad_utf8_async.txt"
    bad_file.write_bytes(b"http://proxy.com:8080\n\xff\xfe\n")
    with pytest.raises(UnicodeDecodeError):
        async for _ in proxy_server_class.from_file_async(
            bad_file, ignore_invalid=True, encoding_errors="strict"
        ):
            pass


def test_host_value_type_exported_from_package() -> None:
    """Tests HostValueType enum is directly importable from proxy_string package."""
    from proxy_string import HostValueType as ImportedHostValueType

    assert ImportedHostValueType.HOSTNAME == "hostname"


def test_with_protocol_accepts_string(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that with_protocol accepts a string protocol name."""
    proxy = proxy_server_class(
        host="example.com", port=8080, protocol=ProxyServerProtocol.HTTP
    )
    p2 = proxy.with_protocol("socks5")
    assert p2.protocol is ProxyServerProtocol.SOCKS5


def test_init_with_positional_protocol_raises_type_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that passing protocol positionally raises TypeError."""
    with pytest.raises(TypeError):
        proxy_server_class("proxy.com", 8080, "http")  # type: ignore[misc]


def test_from_string_with_positional_format_raises_type_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that passing string_format positionally to from_string raises TypeError."""
    with pytest.raises(TypeError):
        proxy_server_class.from_string("proxy.com:8080", ProxyStringFormat.HOST_PORT)  # type: ignore[misc]


def test_from_file_with_positional_format_raises_type_error(
    tmp_path: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that passing string_format positionally to from_file raises TypeError."""
    test_file = tmp_path / "proxies.txt"
    test_file.write_text("proxy.com:8080\n", encoding="utf-8")
    with pytest.raises(TypeError):
        list(proxy_server_class.from_file(test_file, ProxyStringFormat.HOST_PORT))  # type: ignore[misc]


@pytest.mark.asyncio
async def test_from_file_async_with_positional_format_raises_type_error(
    tmp_path: Path,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests passing string_format positionally to from_file_async raises TypeError."""
    test_file = tmp_path / "proxies_async.txt"
    test_file.write_text("proxy.com:8080\n", encoding="utf-8")
    with pytest.raises(TypeError):
        async for _ in proxy_server_class.from_file_async(
            test_file,
            ProxyStringFormat.HOST_PORT,  # type: ignore[misc]
        ):
            pass


def test_supported_package_exported_from_package() -> None:
    """Tests that SupportedPackage type is exported in __all__ from proxy_string."""
    import proxy_string

    assert "SupportedPackage" in proxy_string.__all__
    assert hasattr(proxy_string, "SupportedPackage")


@pytest.mark.parametrize(
    "pkg",
    [
        "aiohttp",
        "curl_cffi",
        "httpx",
        "httpx2",
        "playwright",
        "pycurl",
        "requests",
        "urllib",
        "urllib3",
    ],
)
def test_prepare_for_all_supported_packages(
    pkg: Any,
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests prepare_for produces valid config for all SupportedPackage members."""
    proxy = proxy_server_class(host="example.com", port=8080)
    res = proxy.prepare_for(pkg)
    assert res is not None


def test_factory_methods_support_subclassing(
    temp_proxy_file: Path,
) -> None:
    """Tests that factory methods returning Self preserve subclass instance types."""

    class CustomProxy(ProxyServer):
        pass

    p_dict = CustomProxy.from_dict({"host": "proxy.com", "port": 8080})
    p_str = CustomProxy.from_string("proxy.com:8080")
    p_url = CustomProxy.from_url("http://proxy.com:8080")
    p_json = CustomProxy.from_json('{"host": "proxy.com", "port": 8080}')
    p_file = next(CustomProxy.from_file(temp_proxy_file))

    assert isinstance(p_dict, CustomProxy)
    assert isinstance(p_str, CustomProxy)
    assert isinstance(p_url, CustomProxy)
    assert isinstance(p_json, CustomProxy)
    assert isinstance(p_file, CustomProxy)


@pytest.mark.asyncio
async def test_factory_methods_async_support_subclassing(
    temp_proxy_file: Path,
) -> None:
    """Tests from_file_async returning AsyncGenerator[Self, None] preserves subtype."""

    class CustomProxy(ProxyServer):
        pass

    async for p in CustomProxy.from_file_async(temp_proxy_file):
        assert isinstance(p, CustomProxy)
        break


def test_invalid_proxy_string_error_contains_proxy_string_attribute(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that InvalidProxyStringError stores the invalid proxy string."""
    with pytest.raises(InvalidProxyStringError) as exc_info:
        proxy_server_class.from_string("bad:proxy:str:extra:fields:123")
    assert exc_info.value.proxy_string == "bad:proxy:str:extra:fields:123"


def test_invalid_proxy_url_error_contains_url_attribute(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that InvalidProxyURLError stores the invalid URL."""
    with pytest.raises(InvalidProxyURLError) as exc_info:
        proxy_server_class.from_url("not_an_absolute_url")
    assert exc_info.value.url == "not_an_absolute_url"


def test_protocol_constraint_error_contains_attributes(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that ProtocolConstraintError stores protocol and host."""
    with pytest.raises(ProtocolConstraintError) as exc_info:
        proxy_server_class(host="2001:db8::1", protocol="socks4")
    assert exc_info.value.protocol == ProxyServerProtocol.SOCKS4
    assert exc_info.value.host == "2001:db8::1"


def test_unsupported_package_error_contains_package_name_attribute(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that UnsupportedPackageError stores the package name."""
    proxy = proxy_server_class(host="proxy.com", port=8080)
    with pytest.raises(UnsupportedPackageError) as exc_info:
        proxy.prepare_for("unknown_client_library")  # type: ignore[arg-type]
    assert exc_info.value.package_name == "unknown_client_library"


def test_protocol_not_supported_error_contains_attributes(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that ProtocolNotSupportedError stores package name and protocol."""
    proxy = proxy_server_class(host="proxy.com", port=1080, protocol="socks5")
    with pytest.raises(ProtocolNotSupportedError) as exc_info:
        proxy.prepare_for("urllib")
    assert exc_info.value.package_name == "urllib"
    assert exc_info.value.protocol == "socks5"


def test_proxy_string_format_values_match_string_templates() -> None:
    """Tests ProxyStringFormat members inherit from str and have expected values."""
    assert issubclass(ProxyStringFormat, str)
    assert ProxyStringFormat.URL == "url"
    assert ProxyStringFormat.HOST_PORT == "host:port"
    assert ProxyStringFormat.USER_PASS_HOST_PORT == "user:pass:host:port"
    assert ProxyStringFormat.USER_PASS_AT_HOST_PORT == "user:pass@host:port"
    assert ProxyStringFormat.HOST_PORT_USER_PASS == "host:port:user:pass"
    assert ProxyStringFormat.HOST_PORT_AT_USER_PASS == "host:port@user:pass"
    assert isinstance(ProxyStringFormat.URL, str)


@pytest.mark.parametrize(
    "invalid_dict",
    [
        {},
        {"port": 8080},
        {"host": ""},
        {"host": None},
    ],
)
def test_from_dict_missing_or_empty_host_raises_proxy_configuration_error(
    proxy_server_class: type[ProxyServer],
    invalid_dict: dict[str, Any],
) -> None:
    """Tests from_dict raises ProxyConfigurationError when host is missing or empty."""
    with pytest.raises(
        ProxyConfigurationError,
        match=r"Input dictionary must contain a non-empty 'host' key\.",
    ):
        proxy_server_class.from_dict(invalid_dict)


@pytest.mark.parametrize(
    ("username", "password", "expected"),
    [
        (None, None, False),
        ("admin", None, True),
        (None, "secret", True),
        ("admin", "secret", True),
    ],
)
def test_is_authenticated_with_credentials_returns_expected_boolean(
    proxy_server_class: type[ProxyServer],
    username: str | None,
    password: str | None,
    expected: bool,
) -> None:
    """Tests is_authenticated property with various combinations of credentials."""
    proxy = proxy_server_class(
        host="proxy.com", port=8080, username=username, password=password
    )
    assert proxy.is_authenticated is expected


@pytest.mark.parametrize(
    ("protocol", "expected"),
    [
        (ProxyServerProtocol.HTTP, False),
        (ProxyServerProtocol.HTTPS, False),
        (ProxyServerProtocol.SOCKS4, True),
        (ProxyServerProtocol.SOCKS5, True),
    ],
)
def test_is_socks_with_all_protocols_returns_expected_boolean(
    proxy_server_class: type[ProxyServer],
    protocol: ProxyServerProtocol,
    expected: bool,
) -> None:
    """Tests is_socks property across all supported proxy protocols."""
    proxy = proxy_server_class(host="proxy.com", port=1080, protocol=protocol)
    assert proxy.is_socks is expected


@pytest.mark.parametrize(
    ("protocol", "expected"),
    [
        (ProxyServerProtocol.HTTP, False),
        (ProxyServerProtocol.HTTPS, True),
        (ProxyServerProtocol.SOCKS4, False),
        (ProxyServerProtocol.SOCKS5, False),
    ],
)
def test_is_ssl_with_all_protocols_returns_expected_boolean(
    proxy_server_class: type[ProxyServer],
    protocol: ProxyServerProtocol,
    expected: bool,
) -> None:
    """Tests is_ssl property across all supported proxy protocols."""
    proxy = proxy_server_class(host="proxy.com", port=443, protocol=protocol)
    assert proxy.is_ssl is expected


def test_init_invalid_protocol_type_raises_type_error(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests that passing non-string and non-enum protocol raises TypeError."""
    with pytest.raises(TypeError, match="must be str or ProxyServerProtocol"):
        proxy_server_class(host="proxy.com", protocol=123)  # type: ignore[arg-type]


def test_prepare_for_overloads_return_expected_types(
    proxy_server_class: type[ProxyServer],
) -> None:
    """Tests prepare_for return types across different library groups."""
    proxy = proxy_server_class(
        host="proxy.com", port=8080, username="user", password="pwd"
    )
    urllib_res: dict[str, str] = proxy.prepare_for("urllib")
    assert isinstance(urllib_res, dict)
    assert "http" in urllib_res and "https" in urllib_res

    requests_res: dict[str, str] = proxy.prepare_for("requests")
    assert isinstance(requests_res, dict)
    assert "http" in requests_res and "https" in requests_res

    playwright_res: dict[str, str | None] = proxy.prepare_for("playwright")
    assert isinstance(playwright_res, dict)
    assert playwright_res["server"] == "http://proxy.com:8080"
    assert playwright_res["username"] == "user"
    assert playwright_res["password"] == "pwd"

    httpx_res: str = proxy.prepare_for("httpx")
    assert isinstance(httpx_res, str)
    assert httpx_res == "http://user:pwd@proxy.com:8080"
