"""Proxy server data representation and parser package."""

from .base import ProxyServer, SupportedPackage
from .enums import HostValueType, ProxyServerProtocol, ProxyStringFormat
from .exceptions import (
    InvalidProxyStringError,
    InvalidProxyURLError,
    ProtocolConstraintError,
    ProtocolNotSupportedError,
    ProxyConfigurationError,
    ProxyStringError,
    UnsupportedPackageError,
)

__version__ = "1.0.1"
__all__ = [
    "HostValueType",
    "InvalidProxyStringError",
    "InvalidProxyURLError",
    "ProtocolConstraintError",
    "ProtocolNotSupportedError",
    "ProxyConfigurationError",
    "ProxyServer",
    "ProxyServerProtocol",
    "ProxyStringError",
    "ProxyStringFormat",
    "SupportedPackage",
    "UnsupportedPackageError",
]
