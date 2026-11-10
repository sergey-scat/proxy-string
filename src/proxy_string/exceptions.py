"""Exceptions for proxy-string."""


class ProxyStringError(Exception):
    """Base exception for all proxy-string errors."""


class InvalidProxyStringError(ProxyStringError):
    """Raised when the input proxy string is invalid or cannot be parsed."""

    def __init__(self, message: str, *, proxy_string: str | None = None) -> None:
        super().__init__(message)
        self.proxy_string = proxy_string


class InvalidProxyURLError(ProxyStringError):
    """Raised when the input proxy URL is malformed or invalid."""

    def __init__(self, message: str, *, url: str | None = None) -> None:
        super().__init__(message)
        self.url = url


class ProxyConfigurationError(ProxyStringError):
    """Base exception for proxy configuration and constraint errors."""


class ProtocolConstraintError(ProxyConfigurationError):
    """Raised when protocol network constraints are violated."""

    def __init__(
        self,
        message: str,
        *,
        protocol: str | None = None,
        host: str | None = None,
    ) -> None:
        super().__init__(message)
        self.protocol = protocol
        self.host = host


class UnsupportedPackageError(ProxyConfigurationError):
    """Raised when a third-party client library is not supported."""

    def __init__(self, message: str, *, package_name: str | None = None) -> None:
        super().__init__(message)
        self.package_name = package_name


class ProtocolNotSupportedError(ProxyConfigurationError):
    """Raised when a proxy protocol is not supported by the target library."""

    def __init__(
        self,
        message: str,
        *,
        package_name: str | None = None,
        protocol: str | None = None,
    ) -> None:
        super().__init__(message)
        self.package_name = package_name
        self.protocol = protocol
