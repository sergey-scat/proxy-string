"""Parsers and regex patterns for text-formatted proxy strings."""

import re
from contextlib import suppress
from typing import Any

from .enums import ProxyStringFormat
from .exceptions import InvalidProxyStringError, ProxyStringError
from .whatwg_url import parse_url

PROXY_STRING_FORMATS = {
    ProxyStringFormat.HOST_PORT: "{host}:{port}",
    ProxyStringFormat.USER_PASS_HOST_PORT: "{username}:{password}:{host}:{port}",
    ProxyStringFormat.USER_PASS_AT_HOST_PORT: "{username}:{password}@{host}:{port}",
    ProxyStringFormat.HOST_PORT_USER_PASS: "{host}:{port}:{username}:{password}",
    ProxyStringFormat.HOST_PORT_AT_USER_PASS: "{host}:{port}@{username}:{password}",
}

VALID_IPV6_ADDRESS_REGEX = (
    r"(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}"
    r"|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})"
    r"|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)"
    r"|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}"
    r"|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
    r"(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])"
    r"|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
    r"(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9]))"
)
HOST_PATTERN = rf"(?P<host>[^@:\s]+|\[?{VALID_IPV6_ADDRESS_REGEX}\]?)"
PORT_PATTERN = (
    r"(?P<port>(?:6553[0-5]|655[0-2][0-9]|65[0-4][0-9]{2}|"
    r"6[0-4][0-9]{3}|[1-5][0-9]{4}|[0-9]{1,4}))"
)
USERNAME_PATTERN = r"(?P<username>[^@:\s]*)"
PASSWORD_PATTERN = r"(?P<password>[^@:\s]*)"

PROXY_FORMAT_REGEXPS = {}
for psf_name, psf_value in PROXY_STRING_FORMATS.items():
    re_pattern = psf_value.format(
        host=HOST_PATTERN,
        port=PORT_PATTERN,
        username=USERNAME_PATTERN,
        password=PASSWORD_PATTERN,
    )
    re_pattern = "^" + re_pattern + "$"
    PROXY_FORMAT_REGEXPS[psf_name] = re.compile(re_pattern)


def parse_proxy_string(
    proxy_string: str,
    proxy_format: ProxyStringFormat,
) -> dict[str, Any]:
    """Parses a proxy string according to the specified format.

    Args:
        proxy_string: Proxy string to parse.
        proxy_format: Expected ProxyStringFormat.

    Returns:
        dict[str, Any]: Extracted proxy parameters (host, port, username, password).

    Raises:
        InvalidProxyStringError: If the string does not match the expected format.
    """
    proxy_string = proxy_string.strip()
    if proxy_format == ProxyStringFormat.URL:
        return parse_url(proxy_string)

    match = PROXY_FORMAT_REGEXPS[proxy_format].match(proxy_string)
    if match is not None:
        groups = match.groupdict()
        username = groups.get("username")
        password = groups.get("password")
        if username == "" and password == "":
            username = None
            password = None
        return {
            "host": groups["host"],
            "port": int(groups["port"]),
            "username": username or None,
            "password": password,
        }

    raise InvalidProxyStringError(
        "Unable to parse the proxy string: invalid format.", proxy_string=proxy_string
    )


def detect_possible_formats(
    proxy_string: str,
) -> tuple[tuple[ProxyStringFormat, dict[str, Any]], ...]:
    """Detects viable proxy string formats and attempts to parse the string.

    Note:
        When credentials (usernames or passwords) contain only digits and fall into
        a valid port range (0..65535), 4-part colon-delimited strings can be ambiguous.
        Explicitly passing `ProxyStringFormat` is recommended in such cases.

    Args:
        proxy_string: Raw proxy string without scheme.

    Returns:
        tuple[tuple[ProxyStringFormat, dict[str, Any]], ...]: Parsed formats
            and data dictionaries.
    """
    proxy_string = proxy_string.strip()

    # (1) check if proxy string is an URL
    if "://" in proxy_string:
        with suppress(ProxyStringError, ValueError):
            return (
                (
                    ProxyStringFormat.URL,
                    parse_proxy_string(proxy_string, ProxyStringFormat.URL),
                ),
            )
        return ()

    matches: list[tuple[ProxyStringFormat, dict[str, Any]]] = []

    # (2) check if proxy string contains "@" ("u:p@h:p" or "h:p@u:p")
    if "@" in proxy_string:
        possible_formats = (
            ProxyStringFormat.USER_PASS_AT_HOST_PORT,
            ProxyStringFormat.HOST_PORT_AT_USER_PASS,
        )
        for fmt in possible_formats:
            with suppress(ProxyStringError, ValueError):
                matches.append((fmt, parse_proxy_string(proxy_string, fmt)))
        return tuple(matches)

    # (3) check if proxy string is just host + port (hostname and IPv4 only)
    if proxy_string.count(":") == 1:
        with suppress(ProxyStringError, ValueError):
            return (
                (
                    ProxyStringFormat.HOST_PORT,
                    parse_proxy_string(proxy_string, ProxyStringFormat.HOST_PORT),
                ),
            )
        return ()

    # (4) check for the rest formats
    possible_formats = (
        ProxyStringFormat.HOST_PORT,  # actually, for IPv6 only
        ProxyStringFormat.HOST_PORT_USER_PASS,
        ProxyStringFormat.USER_PASS_HOST_PORT,
    )
    for fmt in possible_formats:
        with suppress(ProxyStringError, ValueError):
            matches.append((fmt, parse_proxy_string(proxy_string, fmt)))
    return tuple(matches)
