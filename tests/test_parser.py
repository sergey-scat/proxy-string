"""Unit tests for proxy string and URL parsing functionality."""

from typing import Any

import proxy_string.whatwg_url as whatwg_url_module
import pytest
from proxy_string import (
    InvalidProxyStringError,
    InvalidProxyURLError,
    ProtocolConstraintError,
)
from proxy_string.enums import (
    HostValueType,
    ProxyServerProtocol,
    ProxyStringFormat,
)
from proxy_string.parsers import detect_possible_formats, parse_proxy_string
from proxy_string.whatwg_url import (
    AVAILABLE_BACKENDS,
    clear_cache,
    decode_idna,
    parse_url,
)


class TestWhatwgUrlParser:
    """Tests for URL parsing with WHATWG backends."""

    @pytest.mark.parametrize(
        (
            "url",
            "expected_protocol",
            "expected_host",
            "expected_port",
            "expected_host_type",
        ),
        [
            (
                "http://proxy.com:8080",
                ProxyServerProtocol.HTTP,
                "proxy.com",
                8080,
                HostValueType.HOSTNAME,
            ),
            (
                "https://proxy.com",
                ProxyServerProtocol.HTTPS,
                "proxy.com",
                443,
                HostValueType.HOSTNAME,
            ),
            (
                "socks4://127.0.0.1:1080",
                ProxyServerProtocol.SOCKS4,
                "127.0.0.1",
                1080,
                HostValueType.IPV4,
            ),
            (
                "socks5://[2001:db8::1]:1080",
                ProxyServerProtocol.SOCKS5,
                "2001:db8::1",
                1080,
                HostValueType.IPV6,
            ),
            (
                "socks5h://example.org:1080",
                ProxyServerProtocol.SOCKS5,
                "example.org",
                1080,
                HostValueType.HOSTNAME,
            ),
            (
                "socks4a://10.0.0.1:1080",
                ProxyServerProtocol.SOCKS4,
                "10.0.0.1",
                1080,
                HostValueType.IPV4,
            ),
            (
                "http://xn--h1adldfi.xn--p1ai:8080",
                ProxyServerProtocol.HTTP,
                "xn--h1adldfi.xn--p1ai",
                8080,
                HostValueType.HOSTNAME,
            ),
        ],
    )
    def test_parse_url_valid_schemes_parsed_correctly(
        self,
        url: str,
        expected_protocol: ProxyServerProtocol,
        expected_host: str,
        expected_port: int,
        expected_host_type: HostValueType,
    ) -> None:
        result = parse_url(url)
        assert result["protocol"] == expected_protocol
        assert result["host"] == expected_host
        assert result["port"] == expected_port
        assert result["host_value_type"] == expected_host_type

    @pytest.mark.parametrize(
        ("url", "expected_user", "expected_pass"),
        [
            ("http://user:pass@proxy.com:8080", "user", "pass"),
            ("http://admin:@proxy.com:8080", "admin", ""),
            ("http://admin@proxy.com:8080", "admin", None),
            ("http://user%3Aname:p%40ss@proxy.com:8080", "user:name", "p@ss"),
            (
                "http://%D0%B2%D0%B0%D1%81%D1%8F:%D1%81%D0%B5%D0%BA%D1%80%D0%B5%D1%82@proxy.com:8080",
                "вася",
                "секрет",
            ),
            ("http://proxy.com:8080", None, None),
        ],
    )
    def test_parse_url_credentials_unquoted_properly(
        self,
        url: str,
        expected_user: str | None,
        expected_pass: str | None,
    ) -> None:
        result = parse_url(url)
        assert result["username"] == expected_user
        assert result["password"] == expected_pass

    @pytest.mark.parametrize(
        ("url", "expected_port"),
        [
            ("http://proxy.com", 80),
            ("https://proxy.com", 443),
            ("socks4://127.0.0.1", 1080),
            ("socks5://127.0.0.1", 1080),
            ("http://proxy.com:0", 80),
        ],
    )
    def test_parse_url_default_ports_applied(
        self, url: str, expected_port: int
    ) -> None:
        result = parse_url(url)
        assert result["port"] == expected_port

    @pytest.mark.parametrize(
        ("url", "expected_port"),
        [
            ("https://proxy.com:80", 80),
            ("socks4://127.0.0.1:80", 80),
            ("socks5://127.0.0.1:80", 80),
            ("socks4a://proxy.com:80", 80),
            ("socks5h://proxy.com:80", 80),
            ("http://[2001:db8::1]", 80),
            ("socks5://[2001:db8::1]:80", 80),
            ("https://user:pass@[2001:db8::1]:80", 80),
        ],
    )
    def test_parse_url_explicit_port_eighty_preserved_for_all_protocols(
        self, url: str, expected_port: int
    ) -> None:
        """Tests explicit port 80 is preserved for non-HTTP schemes."""
        result = parse_url(url)
        assert result["port"] == expected_port

    def test_parse_url_missing_scheme_delimiter_raises_invalid_proxy_url_error(
        self,
    ) -> None:
        with pytest.raises(
            InvalidProxyURLError, match="Proxy URL must be a valid absolute URL!"
        ):
            parse_url("localhost:8080")

    @pytest.mark.parametrize("url", ["ftp://proxy.com:21", "ws://proxy.com:80"])
    def test_parse_url_unsupported_scheme_raises_invalid_proxy_url_error(
        self, url: str
    ) -> None:
        with pytest.raises(InvalidProxyURLError, match="Invalid proxy scheme"):
            parse_url(url)

    def test_parse_url_missing_host_raises_invalid_proxy_url_error(self) -> None:
        with pytest.raises(InvalidProxyURLError):
            parse_url("http://:8080")

    def test_parse_url_empty_hostname_raises_invalid_proxy_url_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class DummyParsedUrl:
            hostname = None

        orig_parse = getattr(
            whatwg_url_module, f"{whatwg_url_module.CURRENT_BACKEND}_parse"
        )
        monkeypatch.setattr(
            whatwg_url_module,
            f"{whatwg_url_module.CURRENT_BACKEND}_parse",
            lambda u: DummyParsedUrl(),
        )
        clear_cache()
        try:
            with pytest.raises(
                InvalidProxyURLError, match="Proxy URL host is required"
            ):
                parse_url("http://dummy_url:8080")
        finally:
            monkeypatch.setattr(
                whatwg_url_module,
                f"{whatwg_url_module.CURRENT_BACKEND}_parse",
                orig_parse,
            )
            clear_cache()

    def test_parse_url_socks4_with_ipv6_raises_protocol_constraint_error(self) -> None:
        with pytest.raises(
            ProtocolConstraintError,
            match="SOCKS4 protocol does not support IPv6 addresses",
        ):
            parse_url("socks4://[2001:db8::1]:1080")

    @pytest.mark.parametrize(
        ("punycode", "expected_unicode"),
        [
            ("xn--h1adldfi.xn--p1ai", "прокси.рф"),
            ("xn--mnq04g52d6ywo0o.xn--fiqs8s", "代理服务器.中国"),
            ("google.com", "google.com"),
        ],
    )
    def test_decode_idna_domains_decoded_correctly(
        self, punycode: str, expected_unicode: str
    ) -> None:
        assert decode_idna(punycode) == expected_unicode

    def test_decode_idna_all_available_backends(self) -> None:
        orig_backend = whatwg_url_module.CURRENT_BACKEND
        try:
            for backend in AVAILABLE_BACKENDS:
                whatwg_url_module.CURRENT_BACKEND = backend
                decode_idna.cache_clear()
                assert decode_idna("xn--h1adldfi.xn--p1ai") == "прокси.рф"
        finally:
            whatwg_url_module.CURRENT_BACKEND = orig_backend
            decode_idna.cache_clear()

    @pytest.mark.skipif(
        "ada_url" not in AVAILABLE_BACKENDS, reason="ada_url is not installed"
    )
    def test_parse_url_invalid_url_error_message_preserves_original_scheme_and_url(
        self,
    ) -> None:
        """Tests InvalidProxyURLError message preserves original scheme."""
        with pytest.raises(
            InvalidProxyURLError, match=r"Invalid proxy URL: 'socks5://bad host'"
        ):
            parse_url("socks5://bad host")

    def test_detect_host_type_ada_url_branches(self) -> None:
        orig_backend = whatwg_url_module.CURRENT_BACKEND
        try:
            whatwg_url_module.CURRENT_BACKEND = "ada_url"
            clear_cache()

            res_v4 = parse_url("http://127.0.0.1:8080")
            assert res_v4["host_value_type"] == HostValueType.IPV4

            res_v6 = parse_url("http://[2001:db8::1]:1080")
            assert res_v6["host_value_type"] == HostValueType.IPV6

            res_host = parse_url("http://example.com:8080")
            assert res_host["host_value_type"] == HostValueType.HOSTNAME
        finally:
            whatwg_url_module.CURRENT_BACKEND = orig_backend
            clear_cache()

    def test_parse_url_switching_backend_works(self) -> None:
        if len(AVAILABLE_BACKENDS) > 1:
            orig = whatwg_url_module.CURRENT_BACKEND
            try:
                for backend in AVAILABLE_BACKENDS:
                    whatwg_url_module.CURRENT_BACKEND = backend
                    clear_cache()
                    res = parse_url("http://user:pass@127.0.0.1:8080")
                    assert res["host"] == "127.0.0.1"
                    assert res["port"] == 8080
            finally:
                whatwg_url_module.CURRENT_BACKEND = orig
                clear_cache()

    def test_no_backends_found_raises_proxy_string_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import importlib

        orig_import = __import__

        def failing_import(name, *args, **kwargs):
            if name in ("can_ada", "ada_url", "pywhatwgurl"):
                raise ImportError(f"Simulated missing {name}")
            return orig_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", failing_import)
        with pytest.raises(
            whatwg_url_module.ProxyStringError, match="No WHATWG/URL backend found!"
        ):
            importlib.reload(whatwg_url_module)

        monkeypatch.undo()
        importlib.reload(whatwg_url_module)

    def test_parse_url_mutation_does_not_affect_subsequent_calls(self) -> None:
        """Tests that mutating dict returned by parse_url does not corrupt cache."""
        res1 = parse_url("http://example.com:8080")
        res1["port"] = 9999
        res1["protocol"] = ProxyServerProtocol.SOCKS5
        res2 = parse_url("http://example.com:8080")
        assert res2["port"] == 8080
        assert res2["protocol"] is ProxyServerProtocol.HTTP


class TestStringParsers:
    """Tests for parse_proxy_string and format detection."""

    @pytest.mark.parametrize(
        ("proxy_str", "fmt", "expected"),
        [
            (
                "1.2.3.4:8080",
                ProxyStringFormat.HOST_PORT,
                {"host": "1.2.3.4", "port": 8080, "username": None, "password": None},
            ),
            (
                "user:pass:1.2.3.4:8080",
                ProxyStringFormat.USER_PASS_HOST_PORT,
                {
                    "host": "1.2.3.4",
                    "port": 8080,
                    "username": "user",
                    "password": "pass",
                },
            ),
            (
                "user:pass@1.2.3.4:8080",
                ProxyStringFormat.USER_PASS_AT_HOST_PORT,
                {
                    "host": "1.2.3.4",
                    "port": 8080,
                    "username": "user",
                    "password": "pass",
                },
            ),
            (
                "1.2.3.4:8080:user:pass",
                ProxyStringFormat.HOST_PORT_USER_PASS,
                {
                    "host": "1.2.3.4",
                    "port": 8080,
                    "username": "user",
                    "password": "pass",
                },
            ),
            (
                "1.2.3.4:8080@user:pass",
                ProxyStringFormat.HOST_PORT_AT_USER_PASS,
                {
                    "host": "1.2.3.4",
                    "port": 8080,
                    "username": "user",
                    "password": "pass",
                },
            ),
            (
                "[2001:db8::1]:8080",
                ProxyStringFormat.HOST_PORT,
                {
                    "host": "[2001:db8::1]",
                    "port": 8080,
                    "username": None,
                    "password": None,
                },
            ),
            (
                "http://user:pass@1.2.3.4:8080",
                ProxyStringFormat.URL,
                {
                    "host": "1.2.3.4",
                    "port": 8080,
                    "username": "user",
                    "password": "pass",
                },
            ),
        ],
    )
    def test_parse_proxy_string_valid_formats_parsed(
        self,
        proxy_str: str,
        fmt: ProxyStringFormat,
        expected: dict[str, Any],
    ) -> None:
        result = parse_proxy_string(proxy_str, fmt)
        assert result["host"] == expected["host"]
        assert result["port"] == expected["port"]
        assert result["username"] == expected["username"]
        assert result["password"] == expected["password"]

    @pytest.mark.parametrize("port", [0, 1, 65529, 65530, 65534, 65535])
    def test_parse_proxy_string_boundary_ports_parsed_correctly(
        self, port: int
    ) -> None:
        result = parse_proxy_string(f"1.2.3.4:{port}", ProxyStringFormat.HOST_PORT)
        assert result["port"] == port

    def test_parse_proxy_string_invalid_format_raises_invalid_proxy_string_error(
        self,
    ) -> None:
        with pytest.raises(
            InvalidProxyStringError,
            match="Unable to parse the proxy string: invalid format",
        ):
            parse_proxy_string("invalid_proxy_format", ProxyStringFormat.HOST_PORT)

    @pytest.mark.parametrize(
        ("proxy_str", "expected_first_format"),
        [
            ("http://proxy.com:8080", ProxyStringFormat.URL),
            ("user:pass@proxy.com:8080", ProxyStringFormat.USER_PASS_AT_HOST_PORT),
            ("proxy.com:8080@user:pass", ProxyStringFormat.HOST_PORT_AT_USER_PASS),
            ("proxy.com:8080", ProxyStringFormat.HOST_PORT),
            ("user:pass:proxy.com:8080", ProxyStringFormat.USER_PASS_HOST_PORT),
            ("[2001:db8::1]:8080", ProxyStringFormat.HOST_PORT),
        ],
    )
    def test_detect_possible_formats_identifies_matching_formats(
        self,
        proxy_str: str,
        expected_first_format: ProxyStringFormat,
    ) -> None:
        matches = detect_possible_formats(proxy_str)
        assert len(matches) > 0
        formats = [m[0] for m in matches]
        assert expected_first_format in formats

    @pytest.mark.parametrize(
        "unparseable_str",
        [
            "not_a_valid_proxy_string",
            "not_a_valid:proxy_string",
            "127.0.0.1:99999",
            "http://",
            "invalid://bad url",
            "user:pass@invalid:99999",
        ],
    )
    def test_detect_possible_formats_unparseable_strings_return_empty_tuple(
        self, unparseable_str: str
    ) -> None:
        """Tests detect_possible_formats returns empty tuple for malformed strings."""
        matches = detect_possible_formats(unparseable_str)
        assert matches == ()

    def test_parse_proxy_string_empty_credentials_parsed_as_none(self) -> None:
        """Tests that colon-delimited string with empty credentials resolves to None."""
        res = parse_proxy_string(
            "1.2.3.4:8080::", ProxyStringFormat.HOST_PORT_USER_PASS
        )
        assert res["username"] is None
        assert res["password"] is None

    @pytest.mark.parametrize(
        ("raw_str", "fmt", "expected_host", "expected_port"),
        [
            ("   1.2.3.4:8080   ", ProxyStringFormat.HOST_PORT, "1.2.3.4", 8080),
            (
                "  user:pass@1.2.3.4:8080  ",
                ProxyStringFormat.USER_PASS_AT_HOST_PORT,
                "1.2.3.4",
                8080,
            ),
        ],
    )
    def test_parse_proxy_string_whitespace_padded_parses_successfully(
        self,
        raw_str: str,
        fmt: ProxyStringFormat,
        expected_host: str,
        expected_port: int,
    ) -> None:
        """Tests parse_proxy_string automatically strips leading/trailing whitespace."""
        result = parse_proxy_string(raw_str, fmt)
        assert result["host"] == expected_host
        assert result["port"] == expected_port

    def test_detect_possible_formats_whitespace_padded_matches_formats(self) -> None:
        """Tests detect_possible_formats automatically strips surrounding whitespace."""
        matches = detect_possible_formats("   1.2.3.4:8080   ")
        assert len(matches) > 0
        assert matches[0][0] is ProxyStringFormat.HOST_PORT


def test_ipv6_regex_contains_no_capturing_groups() -> None:
    """Tests that VALID_IPV6_ADDRESS_REGEX has zero unneeded capturing groups."""
    import re

    from proxy_string.parsers import VALID_IPV6_ADDRESS_REGEX

    compiled = re.compile(VALID_IPV6_ADDRESS_REGEX)
    assert compiled.groups == 0


def test_available_backends_is_tuple() -> None:
    """Tests that AVAILABLE_BACKENDS is exported as a tuple of strings."""
    from proxy_string.whatwg_url import AVAILABLE_BACKENDS

    assert isinstance(AVAILABLE_BACKENDS, tuple)
