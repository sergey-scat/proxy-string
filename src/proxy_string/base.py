"""Main ProxyServer data class and conversion methods."""

import json
from collections.abc import AsyncGenerator, Generator, Mapping
from contextlib import suppress
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Any, Literal, Self, overload

import aiofiles
from attrs import evolve, field, frozen, validators

from . import url_tools
from .enums import HostValueType, ProxyServerProtocol, ProxyStringFormat
from .exceptions import (
    InvalidProxyStringError,
    ProtocolConstraintError,
    ProtocolNotSupportedError,
    ProxyConfigurationError,
    ProxyStringError,
    UnsupportedPackageError,
)
from .parsers import PROXY_STRING_FORMATS, detect_possible_formats, parse_proxy_string
from .whatwg_url import decode_idna, parse_url

SupportedPackage = Literal[
    "aiohttp",
    "curl_cffi",
    "httpx",
    "httpx2",
    "playwright",
    "pycurl",
    "requests",
    "urllib",
    "urllib3",
]


def _check_for_protocol_support(
    proxy_conn_obj: "ProxyServer",
    package_name: str,
    supported_schemes: tuple[str, ...],
    socks_ext: bool = True,
) -> None:
    """Verifies that proxy protocol scheme is supported by target client library.

    Args:
        proxy_conn_obj: ProxyServer instance to validate.
        package_name: Name of the target client library.
        supported_schemes: Tuple of scheme strings supported by the library.
        socks_ext: Whether to use extended SOCKS schemes.

    Raises:
        ProtocolNotSupportedError: If the scheme is not in supported_schemes.
    """
    scheme = url_tools.get_scheme(
        proxy_conn_obj.protocol,
        proxy_conn_obj.remote_dns,
        socks_ext=socks_ext,
    )
    if scheme not in supported_schemes:
        raise ProtocolNotSupportedError(
            f"Package '{package_name}' does not support the '{scheme}' protocol.",
            package_name=package_name,
            protocol=scheme,
        )


def _validate_protocol(inst: Any, attr: Any, value: ProxyServerProtocol) -> None:
    """Validates that protocol argument is a string or ProxyServerProtocol.

    Args:
        inst: Instance being validated.
        attr: Attribute metadata.
        value: Protocol value to validate.

    Raises:
        TypeError: If value is not a string or ProxyServerProtocol.
    """
    if not isinstance(value, (str, ProxyServerProtocol)):
        raise TypeError(
            f"'{attr.name}' must be str or ProxyServerProtocol (got {value!r})."
        )


@frozen
class ProxyServer:
    """Immutable representation of proxy server connection data and credentials.

    Attributes:
        host: Hostname or IP address of the proxy server.
        port: Connection port number (0..65535).
        protocol: Proxy network protocol (HTTP, HTTPS, SOCKS4, SOCKS5).
        username: Optional authentication username.
        password: Optional authentication password.
        remote_dns: Whether DNS resolution should occur on the proxy server.
        unicode_host: Unicode representation of the host (for IDN/punycode).
        host_value_type: Host classification (HOSTNAME, IPV4, or IPV6).
    """

    # main public properties
    host: str = field(
        validator=[validators.instance_of(str), validators.min_len(1)],
        eq=True,
        hash=True,
        repr=True,
    )
    port: int = field(
        default=0,
        converter=int,
        validator=[validators.ge(0), validators.le(65535)],
        eq=True,
        hash=True,
        repr=True,
    )
    protocol: ProxyServerProtocol = field(
        default=ProxyServerProtocol.HTTP,
        validator=_validate_protocol,
        eq=True,
        hash=True,
        repr=True,
        kw_only=True,
    )
    username: str | None = field(
        default=None,
        validator=validators.optional(validators.instance_of(str)),
        eq=True,
        hash=True,
        repr=lambda v: repr(v) if v is not None else "None",
        kw_only=True,
    )
    password: str | None = field(
        default=None,
        validator=validators.optional(validators.instance_of(str)),
        eq=True,
        hash=True,
        repr=lambda v: "'***'" if v is not None else "None",
        kw_only=True,
    )
    remote_dns: bool | None = field(
        default=None,
        validator=validators.optional(validators.instance_of(bool)),
        eq=True,
        hash=True,
        repr=True,
        kw_only=True,
    )
    # private properties
    _host_value_type: HostValueType | None = field(
        default=None,
        validator=validators.optional(validators.instance_of(HostValueType)),
        eq=False,
        hash=False,
        repr=False,
        kw_only=True,
    )
    _skip_validation: bool = field(
        default=False,
        validator=validators.instance_of(bool),
        eq=False,
        hash=False,
        repr=False,
        kw_only=True,
    )

    def __attrs_post_init__(self) -> None:
        """Sets default port and resolves default remote_dns flag for the protocol."""
        if self._skip_validation:
            if self._host_value_type is None:
                raise ProxyConfigurationError(
                    "The 'host_value_type' parameter must be specified "
                    "when validation is skipped."
                )
            object.__setattr__(self, "_skip_validation", False)
            return

        scheme = url_tools.get_scheme(self.protocol, self.remote_dns)
        if scheme in ("http", "https") and self.remote_dns is True:
            raise ProtocolConstraintError(
                f"{scheme.upper()} protocol does not support remote DNS resolution.",
                protocol=scheme,
                host=self.host,
            )
        elif scheme in ("socks4a", "socks5h") and self.remote_dns is False:
            raise ProtocolConstraintError(
                f"Conflicting configuration: scheme '{scheme}' requires "
                "remote DNS resolution, but 'remote_dns' is set to False.",
                protocol=scheme,
                host=self.host,
            )

        parsed = parse_url(
            url_tools.build_url(
                scheme, self.host, self.port, self.username, self.password
            )
        )

        remote_dns = (
            self.remote_dns if parsed["remote_dns"] is None else parsed["remote_dns"]
        )

        object.__setattr__(self, "protocol", parsed["protocol"])
        object.__setattr__(self, "host", parsed["host"])
        object.__setattr__(self, "port", parsed["port"])
        object.__setattr__(self, "username", parsed["username"])
        object.__setattr__(self, "password", parsed["password"])
        object.__setattr__(self, "remote_dns", remote_dns)
        object.__setattr__(self, "_host_value_type", parsed["host_value_type"])
        object.__setattr__(self, "_skip_validation", False)

    @property
    def url(self) -> str:
        """Returns the full URL representation including credentials.

        Returns:
            str: Absolute proxy URL.
        """
        return self.to_url()

    @property
    def origin(self) -> str:
        """Returns the origin URL excluding authentication credentials.

        Returns:
            str: Proxy origin URL without credentials.
        """
        return self.to_url(exclude_credentials=True)

    @property
    def unicode_host(self) -> str:
        """Returns the host decoded from IDNA Punycode to Unicode if applicable.

        Returns:
            str: Unicode representation of the host name.
        """
        if self._host_value_type is HostValueType.HOSTNAME:
            return decode_idna(self.host)
        return self.host

    @property
    def unicode_url(self) -> str:
        """Returns the URL representation with Unicode host and credentials.

        Returns:
            str: Proxy URL with decoded Unicode hostname.
        """
        scheme = url_tools.get_scheme(self.protocol, self.remote_dns, socks_ext=True)
        return url_tools.build_url(
            scheme, self.unicode_host, self.port, self.username, self.password
        )

    @property
    def host_ip_address(self) -> IPv4Address | IPv6Address | None:
        """Returns the IP address object if the host is an IP, otherwise None.

        Returns:
            IPv4Address | IPv6Address | None: Parsed IP address object or None.
        """
        if self._host_value_type is HostValueType.IPV4:
            return IPv4Address(self.host)
        if self._host_value_type is HostValueType.IPV6:
            return IPv6Address(self.host)
        return None

    @property
    def host_value_type(self) -> HostValueType:
        """Returns the classification of the host (HOSTNAME, IPV4, or IPV6).

        Returns:
            HostValueType: Host classification enum member.
        """
        assert self._host_value_type is not None
        return self._host_value_type

    @property
    def is_authenticated(self) -> bool:
        """Returns True if the proxy has credentials (username or password).

        Returns:
            bool: True if username or password is set, False otherwise.
        """
        return bool(self.username or self.password)

    @property
    def is_socks(self) -> bool:
        """Returns True if the proxy protocol is a SOCKS protocol (SOCKS4 or SOCKS5).

        Returns:
            bool: True if protocol is SOCKS4 or SOCKS5, False otherwise.
        """
        return self.protocol in (
            ProxyServerProtocol.SOCKS4,
            ProxyServerProtocol.SOCKS5,
        )

    @property
    def is_ssl(self) -> bool:
        """Returns True if the proxy connection uses TLS/SSL (HTTPS).

        Returns:
            bool: True if protocol is HTTPS, False otherwise.
        """
        return self.protocol is ProxyServerProtocol.HTTPS

    def __str__(self) -> str:
        """Returns the URL representation of the proxy server."""
        return self.to_url()

    @classmethod
    def from_dict(cls, input_dict: Mapping[str, Any]) -> Self:
        """Creates a ProxyServer instance from a dictionary of parameters.

        Args:
            input_dict: Dictionary containing proxy configuration keys
                ('host', 'port', 'protocol' or 'scheme', 'username',
                'password', 'remote_dns').

        Returns:
            ProxyServer: A new ProxyServer instance.

        Raises:
            TypeError: If input_dict is not a Mapping.
            ProxyConfigurationError: If 'host' is missing or empty.
        """
        if not isinstance(input_dict, Mapping):
            raise TypeError("Input data must be a dictionary or mapping!")

        if "host" not in input_dict or not input_dict["host"]:
            raise ProxyConfigurationError(
                "Input dictionary must contain a non-empty 'host' key."
            )

        port = input_dict.get("port")
        kwargs: dict[str, Any] = {
            "host": input_dict["host"],
            # first try to get "scheme" since scheme can be "socks4a" or "socks5h"
            "protocol": input_dict.get(
                "scheme", input_dict.get("protocol", ProxyServerProtocol.HTTP)
            ),
            "username": input_dict.get("username"),
            "password": input_dict.get("password"),
            "remote_dns": input_dict.get("remote_dns"),
        }
        if port is not None:
            kwargs["port"] = port

        return cls(**kwargs)

    @classmethod
    def from_json(cls, input_json: str) -> Self:
        """Creates a ProxyServer instance from a JSON-formatted string.

        Args:
            input_json: JSON string representing proxy parameters.

        Returns:
            ProxyServer: A new ProxyServer instance.

        Raises:
            json.JSONDecodeError: If input_json is not valid JSON.
        """
        input_dict = json.loads(input_json)
        return cls.from_dict(input_dict)

    @classmethod
    def from_string(
        cls,
        proxy_string: str,
        *,
        string_format: ProxyStringFormat | None = None,
        protocol: ProxyServerProtocol | None = None,
    ) -> Self:
        """Creates a ProxyServer instance by parsing a formatted proxy string.

        Args:
            proxy_string: Formatted proxy string (e.g. 'host:port',
                'user:pass@host:port').
            string_format: Optional explicit ProxyStringFormat to match against.
                Recommended when usernames or passwords are numeric to avoid
                port ambiguity in 4-part colon-delimited strings.
            protocol: Optional protocol override (defaults to parsed protocol or HTTP).

        Returns:
            ProxyServer: A new ProxyServer instance.

        Raises:
            InvalidProxyStringError: If the string does not match the expected format.
        """
        proxy_string = proxy_string.strip()
        if string_format:
            parsed_proxy = dict(parse_proxy_string(proxy_string, string_format))
            if protocol:
                parsed_proxy["protocol"] = protocol
                parsed_proxy.pop("skip_validation", None)
            return cls(**parsed_proxy)

        possible_formats = detect_possible_formats(proxy_string)

        for _, parsed_proxy in possible_formats:
            parsed = dict(parsed_proxy)
            if protocol:
                parsed["protocol"] = protocol
                parsed.pop("skip_validation", None)

            with suppress(ProxyStringError, ValueError):
                return cls(**parsed)

        raise InvalidProxyStringError(
            f"Unable to parse the proxy string: '{proxy_string}'!",
            proxy_string=proxy_string,
        )

    @classmethod
    def from_url(cls, url: str) -> Self:
        """Creates a ProxyServer instance by parsing a proxy URL.

        Args:
            url: A complete proxy URL (e.g. 'http://user:pass@proxy.com:8080').

        Returns:
            ProxyServer: A new ProxyServer instance.

        Raises:
            InvalidProxyURLError: If the URL format, scheme, or host is invalid.
        """
        return cls(**parse_url(url))

    @classmethod
    def from_file(  # noqa: PLR0913
        cls,
        input_file: str | Path,
        *,
        string_format: ProxyStringFormat | None = None,
        protocol: ProxyServerProtocol | None = None,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        ignore_invalid: bool = False,
    ) -> Generator[Self, None, None]:
        """Yields ProxyServer instances by reading proxy strings from a file.

        Args:
            input_file: Path to the proxy text file.
            string_format: Optional explicit ProxyStringFormat for rows.
                Recommended when usernames or passwords are numeric to avoid
                port ambiguity in 4-part colon-delimited strings.
            protocol: Optional protocol override for all rows.
            encoding: Text encoding of the file (defaults to 'utf-8').
            encoding_errors: Text codec error handling mode passed to open()
                (defaults to 'strict').
            ignore_invalid: If True, rows that cannot be parsed are skipped.
                If False (default), raises InvalidProxyStringError or ValueError.

        Yields:
            ProxyServer: Parsed proxy server instances.

        Raises:
            InvalidProxyStringError: If a row cannot be parsed and
                ignore_invalid is False.
        """
        with open(input_file, encoding=encoding, errors=encoding_errors) as infile:
            for row in infile:
                line = row.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    yield cls.from_string(
                        line, string_format=string_format, protocol=protocol
                    )
                except (ProxyStringError, ValueError):
                    if not ignore_invalid:
                        raise

    @classmethod
    async def from_file_async(  # noqa: PLR0913
        cls,
        input_file: str | Path,
        *,
        string_format: ProxyStringFormat | None = None,
        protocol: ProxyServerProtocol | None = None,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        ignore_invalid: bool = False,
    ) -> AsyncGenerator[Self, None]:
        """Asynchronously yields ProxyServer instances by reading a file.

        Args:
            input_file: Path to the proxy text file.
            string_format: Optional explicit ProxyStringFormat for rows.
                Recommended when usernames or passwords are numeric to avoid
                port ambiguity in 4-part colon-delimited strings.
            protocol: Optional protocol override for all rows.
            encoding: Text encoding of the file (defaults to 'utf-8').
            encoding_errors: Text codec error handling mode passed to open()
                (defaults to 'strict').
            ignore_invalid: If True, rows that cannot be parsed are skipped.
                If False (default), raises InvalidProxyStringError or ValueError.

        Yields:
            ProxyServer: Parsed proxy server instances.

        Raises:
            InvalidProxyStringError: If a row cannot be parsed and
                ignore_invalid is False.
        """
        async with aiofiles.open(
            input_file, encoding=encoding, errors=encoding_errors
        ) as infile:
            async for row in infile:
                line = row.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    yield cls.from_string(
                        line, string_format=string_format, protocol=protocol
                    )
                except (ProxyStringError, ValueError):
                    if not ignore_invalid:
                        raise

    def to_dict(self) -> dict[str, Any]:
        """Serializes proxy server attributes into a dictionary.

        Returns:
            dict: Dictionary with host, port, protocol, username, password, remote_dns.
        """
        return {
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "username": self.username,
            "password": self.password,
            "remote_dns": self.remote_dns,
        }

    def to_json(self) -> str:
        """Serializes proxy server attributes into a JSON string.

        Returns:
            str: JSON representation of the proxy server.
        """
        return json.dumps(self.to_dict())

    def to_string(
        self,
        string_format: ProxyStringFormat | None = None,
    ) -> str:
        """Formats the proxy server into a specified or auto-selected string format.

        Args:
            string_format: Format template from ProxyStringFormat. If None,
                defaults to HOST_PORT_USER_PASS when credentials are present,
                otherwise HOST_PORT.

        Returns:
            str: Formatted proxy string.
        """
        if string_format is ProxyStringFormat.URL:
            return self.to_url()

        if string_format is None:
            string_format = (
                ProxyStringFormat.HOST_PORT_USER_PASS
                if self.username is not None or self.password is not None
                else ProxyStringFormat.HOST_PORT
            )

        format_str = PROXY_STRING_FORMATS[string_format]
        return format_str.format(
            host=self.host,
            port=self.port,
            username=self.username or "",
            password=self.password or "",
        )

    def to_url(self, socks_ext: bool = True, exclude_credentials: bool = False) -> str:
        """Serializes proxy server to URL string.

        Args:
            socks_ext: Whether to use extended SOCKS schemes ('socks4a', 'socks5h').
            exclude_credentials: If True, omits username and password from the URL.

        Returns:
            str: Proxy server URL.
        """
        scheme = url_tools.get_scheme(self.protocol, self.remote_dns, socks_ext)

        if exclude_credentials:
            return url_tools.build_url(scheme, self.host, self.port)
        return url_tools.build_url(
            scheme, self.host, self.port, self.username, self.password
        )

    def with_host(self, host: str) -> Self:
        """Returns a copy of the proxy with a modified host.

        Args:
            host: The new host name or IP address.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, host=host)

    def with_port(self, port: int) -> Self:
        """Returns a copy of the proxy with a modified port.

        Args:
            port: The new port number.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, port=port)

    def with_protocol(self, protocol: ProxyServerProtocol | str) -> Self:
        """Returns a copy of the proxy with a modified protocol.

        Args:
            protocol: The new proxy protocol enum member or protocol name string.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, protocol=protocol)

    def with_username(self, username: str | None) -> Self:
        """Returns a copy of the proxy with a modified username.

        Args:
            username: The new username credential.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, username=username)

    def with_password(self, password: str | None) -> Self:
        """Returns a copy of the proxy with a modified password.

        Args:
            password: The new password credential.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, password=password)

    def with_creds(self, username: str | None, password: str | None) -> Self:
        """Returns a copy of the proxy with modified credentials.

        Args:
            username: The new username credential.
            password: The new password credential.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, username=username, password=password)

    def with_remote_dns(self, remote_dns: bool | None) -> Self:
        """Returns a copy of the proxy with a modified remote_dns flag.

        Args:
            remote_dns: Whether DNS resolution should occur on the proxy.

        Returns:
            Self: A new proxy server instance.
        """
        return evolve(self, remote_dns=remote_dns)

    @overload
    def prepare_for(
        self, package_name: Literal["urllib", "requests"]
    ) -> dict[str, str]: ...

    @overload
    def prepare_for(
        self, package_name: Literal["playwright"]
    ) -> dict[str, str | None]: ...

    @overload
    def prepare_for(
        self,
        package_name: Literal[
            "urllib3", "httpx", "httpx2", "aiohttp", "pycurl", "curl_cffi"
        ],
    ) -> str: ...

    @overload
    def prepare_for(
        self, package_name: SupportedPackage | str
    ) -> dict[str, Any] | str: ...

    def prepare_for(self, package_name: SupportedPackage | str) -> dict[str, Any] | str:
        """Prepares proxy configuration for third-party libraries.

        Args:
            package_name: Target library name ('urllib', 'requests', 'urllib3',
                'httpx', 'httpx2', 'aiohttp', 'playwright', 'pycurl', or 'curl_cffi').

        Returns:
            dict[str, Any] | str: Library-specific proxy configuration structure.

        Raises:
            UnsupportedPackageError: If the package is not supported.
            ProtocolNotSupportedError: If the protocol is incompatible.
        """
        match package_name.strip().lower():
            case "urllib":
                _check_for_protocol_support(self, "urllib", ("http", "https"))
                url = self.to_url(socks_ext=True)
                return {"http": url, "https": url}
            case "requests":
                url = self.to_url(socks_ext=True)
                return {"http": url, "https": url}
            case "urllib3" | "httpx" | "httpx2" | "aiohttp" | "pycurl" | "curl_cffi":
                return self.to_url(socks_ext=True)
            case "playwright":
                _check_for_protocol_support(
                    self, "playwright", ("http", "https", "socks5"), socks_ext=False
                )
                return {
                    "server": self.to_url(socks_ext=False, exclude_credentials=True),
                    "username": self.username,
                    "password": self.password,
                }
            case _:
                raise UnsupportedPackageError(
                    f"Package '{package_name}' is not supported.",
                    package_name=package_name,
                )
