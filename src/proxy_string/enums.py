"""Enums for proxy protocols, host types, and string formats."""

from enum import StrEnum


class ProxyServerProtocol(StrEnum):
    """Supported network protocols for proxy servers."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


PROXY_DEFAULT_PORT_BY_PROTOCOL = {
    ProxyServerProtocol.HTTP: 80,
    ProxyServerProtocol.HTTPS: 443,
    ProxyServerProtocol.SOCKS4: 1080,
    ProxyServerProtocol.SOCKS5: 1080,
}


class HostValueType(StrEnum):
    """Classification of the host representation type."""

    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"


class ProxyStringFormat(StrEnum):
    """Supported serialization and parsing formats for proxy strings."""

    URL = "url"
    HOST_PORT = "host:port"
    USER_PASS_HOST_PORT = "user:pass:host:port"
    USER_PASS_AT_HOST_PORT = "user:pass@host:port"
    HOST_PORT_USER_PASS = "host:port:user:pass"
    HOST_PORT_AT_USER_PASS = "host:port@user:pass"
