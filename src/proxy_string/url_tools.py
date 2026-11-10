"""URL parsing, escaping, and scheme resolution helpers."""

from urllib.parse import quote, unquote

from .enums import ProxyServerProtocol


def quote_all(
    input_string: str, encoding: str = "utf-8", errors: str = "strict"
) -> str:
    """Percent-encodes all reserved characters in a string.

    Encodes every character that is not alphanumeric, without treating
    any characters as safe.

    Args:
        input_string: The string to percent-encode.
        encoding: The text encoding to use (defaults to 'utf-8').
        errors: Error handling scheme for decoding errors.

    Returns:
        str: The fully percent-encoded string.
    """
    return quote(input_string, safe="", encoding=encoding, errors=errors)


def unquote_all(
    input_string: str, encoding: str = "utf-8", errors: str = "strict"
) -> str:
    """Decodes percent-encoded characters in a string.

    Args:
        input_string: The percent-encoded string.
        encoding: The text encoding to use (defaults to 'utf-8').
        errors: Error handling scheme for decoding errors.

    Returns:
        str: The decoded string.
    """
    return unquote(input_string, encoding=encoding, errors=errors)


def build_url(
    scheme: str,
    host: str,
    port: int,
    username: str | None = None,
    password: str | None = None,
) -> str:
    """Constructs a standard URL string from individual proxy components.

    Args:
        scheme: The URL scheme/protocol (e.g. 'http', 'socks5h').
        host: Hostname or IP address (IPv6 will be bracketed if needed).
        port: Connection port number.
        username: Optional username credential.
        password: Optional password credential.

    Returns:
        str: Formatted URL string.
    """
    if username is not None and password is not None:
        target_user_passw = f"{quote_all(username)}:{quote_all(password)}@"
    elif username is not None:
        target_user_passw = f"{quote_all(username)}@"
    elif password is not None:
        target_user_passw = f":{quote_all(password)}@"
    else:
        target_user_passw = ""

    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    return f"{scheme}://{target_user_passw}{host}:{port}"


def get_scheme(
    protocol: ProxyServerProtocol | str,
    remote_dns: bool | None,
    socks_ext: bool = True,
) -> str:
    """Determines the appropriate URL scheme based on protocol and DNS resolution mode.

    Args:
        protocol: Proxy protocol enum member or protocol name string.
        remote_dns: Whether remote DNS resolution is enabled.
        socks_ext: Whether to use extended SOCKS schemes ('socks4a', 'socks5h').

    Returns:
        str: Resolved scheme string.
    """
    protocol = protocol.lower()
    if remote_dns and socks_ext:
        if protocol == ProxyServerProtocol.SOCKS4:
            return "socks4a"
        if protocol == ProxyServerProtocol.SOCKS5:
            return "socks5h"
    return protocol


def get_protocol(scheme: str) -> tuple[ProxyServerProtocol, bool | None]:
    """Resolves a scheme name into a ProxyServerProtocol and remote_dns flag.

    Args:
        scheme: URL scheme string (e.g. 'socks5h', 'http').

    Returns:
        tuple[ProxyServerProtocol, bool | None]: Tuple of protocol enum and
            remote_dns setting.

    Raises:
        ValueError: If scheme is not a recognized proxy protocol.
    """
    scheme = scheme.lower()
    if scheme in ("socks5h", "socks4a"):
        remote_dns = True
    elif scheme in ("socks5", "socks4"):
        remote_dns = None
    else:
        remote_dns = False
    protocol = ProxyServerProtocol(
        {"socks5h": "socks5", "socks4a": "socks4"}.get(scheme, scheme)
    )
    return protocol, remote_dns
