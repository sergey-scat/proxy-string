"""WHATWG URL standard backend integration and IDNA decoding."""

from functools import lru_cache
from ipaddress import IPv4Address, ip_address
from typing import Any

from . import url_tools
from .enums import PROXY_DEFAULT_PORT_BY_PROTOCOL, HostValueType, ProxyServerProtocol
from .exceptions import InvalidProxyURLError, ProtocolConstraintError, ProxyStringError

_backends: list[str] = []

try:
    import can_ada

    can_ada_parse = can_ada.parse

    def can_ada_decode(v: str) -> str:
        return can_ada.idna_decode(v.encode())  # type: ignore

    _backends.append("can_ada")
except ImportError:
    pass

try:
    import ada_url

    ada_url_parse = ada_url.URL

    ada_url_decode = ada_url.idna_to_unicode
    ada_url_host_type = ada_url.HostType
    _backends.append("ada_url")
except ImportError:
    pass

try:
    import pywhatwgurl

    pywhatwgurl_parse = pywhatwgurl.URL

    def pywhatwgurl_decode(v: str) -> str:
        return pywhatwgurl.domain_to_unicode(v, be_strict=True)

    _backends.append("pywhatwgurl")
except ImportError:
    pass

if not _backends:
    raise ProxyStringError("No WHATWG/URL backend found!")

AVAILABLE_BACKENDS: tuple[str, ...] = tuple(_backends)
CURRENT_BACKEND: str = AVAILABLE_BACKENDS[0]


def _detect_host_type(host: str, parsed_url: Any) -> HostValueType:
    """Detects host type for the parsed URL.

    Args:
        host: Host string (stripped of brackets if IPv6).
        parsed_url: Parsed URL object from the backend parser.

    Returns:
        HostValueType: Detected classification of the host.
    """
    if CURRENT_BACKEND == "ada_url":
        if parsed_url.host_type is ada_url_host_type.IPV4:
            return HostValueType.IPV4
        if parsed_url.host_type is ada_url_host_type.IPV6:
            return HostValueType.IPV6
        return HostValueType.HOSTNAME

    try:
        addr = ip_address(host)
    except ValueError:
        return HostValueType.HOSTNAME

    return HostValueType.IPV4 if isinstance(addr, IPv4Address) else HostValueType.IPV6


def _extract_explicit_port(uri: str) -> int | None:
    """Extracts an explicit port number from the URI authority component if present.

    Args:
        uri: The URI component following the scheme delimiter '://'.

    Returns:
        int | None: Explicit port number as integer, or None if no port is specified.
    """
    authority = uri.split("/")[0].split("?")[0].split("#")[0]
    host_port = authority.rpartition("@")[2]
    if "]" in host_port:
        after_bracket = host_port.rpartition("]")[2]
        if after_bracket.startswith(":"):
            port_str = after_bracket[1:]
            return int(port_str) if port_str.isdigit() else None
        return None
    if ":" in host_port:
        port_str = host_port.rpartition(":")[2]
        return int(port_str) if port_str.isdigit() else None
    return None


@lru_cache
def _parse_url_cached(url: str) -> dict[str, Any]:
    if "://" not in url:
        raise InvalidProxyURLError("Proxy URL must be a valid absolute URL!", url=url)

    scheme, _, uri = url.partition("://")
    try:
        protocol, remote_dns = url_tools.get_protocol(scheme)
    except ValueError as e:
        raise InvalidProxyURLError(f"Invalid proxy scheme: '{scheme}'", url=url) from e

    parse = globals()[f"{CURRENT_BACKEND}_parse"]

    normalized_url = f"http://{uri}"
    try:
        parsed_url = parse(normalized_url)
    except Exception as e:
        raise InvalidProxyURLError(f"Invalid proxy URL: '{url}'", url=url) from e

    host = parsed_url.hostname
    if not host:
        raise InvalidProxyURLError("Proxy URL host is required.", url=url)

    host = host.strip("[]")
    port_str = parsed_url.port
    parsed_port = int(port_str) if port_str and port_str != "0" else None
    explicit_port = _extract_explicit_port(uri)
    if parsed_port is not None:
        port = parsed_port
    elif explicit_port is not None and explicit_port != 0:
        port = explicit_port
    else:
        port = PROXY_DEFAULT_PORT_BY_PROTOCOL[protocol]

    authority = uri.split("/")[0].split("?")[0].split("#")[0]
    username = (
        url_tools.unquote_all(parsed_url.username) if parsed_url.username else None
    )
    if "@" in authority:
        userinfo = authority.rpartition("@")[0]
        password = (
            url_tools.unquote_all(parsed_url.password) if ":" in userinfo else None
        )
    else:
        password = None

    host_type = _detect_host_type(host, parsed_url)

    if host_type is HostValueType.IPV6 and protocol is ProxyServerProtocol.SOCKS4:
        raise ProtocolConstraintError(
            "SOCKS4 protocol does not support IPv6 addresses.",
            protocol=protocol,
            host=host,
        )

    return {
        "protocol": protocol,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "remote_dns": remote_dns,
        "host_value_type": host_type,
        "skip_validation": True,
    }


def parse_url(url: str) -> dict[str, Any]:
    """Parses a proxy URL into a dictionary of proxy attributes.

    Args:
        url: Absolute proxy URL string.

    Returns:
        dict[str, Any]: Parsed proxy attributes.

    Raises:
        InvalidProxyURLError: If URL has no scheme, missing host, or SOCKS4 is
            used with IPv6.
    """
    return _parse_url_cached(url).copy()


def clear_cache() -> None:
    """Clears internal WHATWG URL and IDNA parser caches."""
    _parse_url_cached.cache_clear()
    decode_idna.cache_clear()


@lru_cache
def decode_idna(encoded_domain: str) -> str:
    """Decodes a punycode/IDNA domain to Unicode.

    Args:
        encoded_domain: Punycode-encoded domain name.

    Returns:
        str: Unicode representation of the domain name.
    """
    decode = globals()[f"{CURRENT_BACKEND}_decode"]
    return decode(encoded_domain)
