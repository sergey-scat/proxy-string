<p align="center">
  <img src="assets/logo.jpg" alt="proxy-string logo" width="220" />
</p>

<h1 align="center">proxy-string</h1>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff" /></a>
  <a href="https://github.com/bwhmather/ty"><img src="https://img.shields.io/badge/types-ty-blueviolet.svg" alt="Checked with ty" /></a>
  <a href="https://github.com/sergey-scat/proxy-string"><img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg" alt="Coverage" /></a>
</p>

<p align="center">
  A lightweight, type-safe Python library for parsing, validating, and converting proxy server connection data.
</p>

<p align="center">
  Supports <strong>HTTP</strong>, <strong>HTTPS</strong>, <strong>SOCKS4</strong>, and <strong>SOCKS5</strong> (including remote DNS schemes <code>socks4a</code> and <code>socks5h</code>), with full compatibility for <strong>IPv4</strong>, <strong>IPv6</strong>, <strong>Unicode credentials</strong>, and <strong>IDN (Punycode)</strong> hostnames.
</p>

---

## Features

- **WHATWG URL Standard Compliance**: URL parsing conforms to modern WHATWG URL standards via `pywhatwgurl` (pure Python, installed by default), with optional high-performance C++ backends (`ada-url` and `can-ada`) selected automatically by speed priority.
- **Unicode & IDN Ready**:
  - Full support for UTF-8 Unicode usernames and passwords with percent-encoding.
  - Transparent support for internationalized domain names (e.g. `代理服务器.中国` ↔ `xn--mnq04g52d6ywo0o.xn--fiqs8s`).
- **Multi-Protocol Support**: Full support for HTTP, HTTPS, SOCKS4, and SOCKS5. Automatically maps `socks4a` and `socks5h` schemes to remote DNS resolution. Enforces protocol constraints (e.g. SOCKS4 IPv6 network restrictions).
- **Flexible Parsing**:
  - Full URLs (e.g. `http://user:pass@192.168.1.1:8080`, `socks5h://...`).
  - Standard text formats (`host:port`, `user:pass:host:port`, `host:port@user:pass`, etc.) with automatic format detection.
  - Dictionaries (`from_dict`) and JSON strings (`from_json`).
  - Batch parsing from text files: synchronous (`from_file`) and asynchronous (`from_file_async`) generators with comment and whitespace filtering.
- **Immutable & Safe**: Data objects are frozen (`@attrs.frozen`), hashable, and comparable. Strict validation for ports (`0..65535`), protocols, and hostnames.
- **Evolution Methods**: Convenient `with_*` methods (`with_host`, `with_port`, `with_protocol`, `with_creds`, etc.) returning modified immutable copies.
- **Third-Party Client Integration**: Built-in `prepare_for()` method returning ready-to-use proxy configuration structures for `requests`, `httpx`, `httpx2`, `aiohttp`, `playwright`, `urllib`, `urllib3`, `pycurl`, and `curl_cffi`, strictly type-checked via `SupportedPackage` Literal.

---

## Installation

Install using `pip`:

```bash
pip install proxy-string
```

Or using [`uv`](https://docs.astral.sh/uv/):

```bash
uv add proxy-string
```

### Optional High-Speed Backends

For maximum URL parsing throughput, install optional C++ WHATWG URL backends:

```bash
# Using pip
pip install "proxy-string[ada_url]"
pip install "proxy-string[can_ada]"

# Using uv
uv add "proxy-string[ada_url]"
uv add "proxy-string[can_ada]"
```

When installed, `proxy-string` automatically selects the fastest available backend:
`can-ada` → `ada-url` → `pywhatwgurl`.

---

## Quick Start

```python
from proxy_string import ProxyServer, ProxyServerProtocol

# 1. Direct initialization (Unicode credentials supported)
proxy = ProxyServer(
    host="proxy.example.com",
    port=8080,
    protocol=ProxyServerProtocol.HTTPS,
    username="юзер",
    password="пароль",
)
print(proxy.to_url())
# https://%D1%8E%D0%B7%D0%B5%D1%80:%D0%BF%D0%B0%D1%80%D0%BE%D0%BB%D1%8C@proxy.example.com:8080

# 2. Parse from URL
socks_proxy = ProxyServer.from_url("socks5h://user:pass@10.0.0.1:1080")
print(socks_proxy.protocol)  # ProxyServerProtocol.SOCKS5
print(socks_proxy.remote_dns)  # True

# 3. Parse from string (automatic format detection)
auto_proxy = ProxyServer.from_string("192.168.1.100:8080:alice:password123")
print(auto_proxy.host)  # '192.168.1.100'
print(auto_proxy.port)  # 8080
print(auto_proxy.username)  # 'alice'
```

---

## Supported String Formats

The `ProxyStringFormat` enum supports the most widely used proxy list formats:

| Enum Member | Pattern Format | Example |
| :--- | :--- | :--- |
| `ProxyStringFormat.URL` | `scheme://[user:pass@]host:port` | `http://user:pass@proxy.com:8080` |
| `ProxyStringFormat.HOST_PORT` | `{host}:{port}` | `192.168.1.1:8080` |
| `ProxyStringFormat.USER_PASS_HOST_PORT` | `{username}:{password}:{host}:{port}` | `user:pass:192.168.1.1:8080` |
| `ProxyStringFormat.USER_PASS_AT_HOST_PORT` | `{username}:{password}@{host}:{port}` | `user:pass@192.168.1.1:8080` |
| `ProxyStringFormat.HOST_PORT_USER_PASS` | `{host}:{port}:{username}:{password}` | `192.168.1.1:8080:user:pass` |
| `ProxyStringFormat.HOST_PORT_AT_USER_PASS` | `{host}:{port}@{username}:{password}` | `192.168.1.1:8080@user:pass` |

When calling `ProxyServer.from_string()` without specifying `string_format`, the format is detected automatically:
- Strings with `://` are parsed as URLs.
- Strings containing `@` match `user:pass@host:port` or `host:port@user:pass`.
- Single-colon strings (`host:port`) match `HOST_PORT`.
- Multi-colon strings match IPv6 `[::1]:8080`, `HOST_PORT_USER_PASS`, or `USER_PASS_HOST_PORT`.

> [!TIP]
> **Ambiguity with numeric credentials:**
> In 4-part colon-delimited formats (`HOST_PORT_USER_PASS` vs `USER_PASS_HOST_PORT`), if the password or username consists only of digits and falls within the valid port range (`0..65535`), automatic detection can be ambiguous. In such cases, pass the explicit `string_format` (e.g. `string_format=ProxyStringFormat.HOST_PORT_USER_PASS`).

---

## Usage Guide

### Reading Proxies from Files

Text files can include empty lines and comment lines prefixed with `#`:

#### Synchronous File Reading

```python
from proxy_string import ProxyServer

# Parse all valid rows, ignoring malformed lines
for proxy in ProxyServer.from_file("proxies.txt", ignore_invalid=True):
    print(proxy.to_url())
```

#### Asynchronous File Reading

Process proxy lists asynchronously using `aiofiles`:

```python
import asyncio
from proxy_string import ProxyServer, ProxyServerProtocol


async def load_proxies():
    async for proxy in ProxyServer.from_file_async(
        "proxies.txt",
        protocol=ProxyServerProtocol.SOCKS5,
        ignore_invalid=True,
    ):
        print(f"Loaded: {proxy.host}:{proxy.port}")


asyncio.run(load_proxies())
```

---

### Exporting and Serialization

#### URL Formatting

```python
proxy = ProxyServer.from_url("socks5h://user:pass@proxy.net:1080")

# Standard URL representation
print(proxy.to_url())
# socks5h://user:pass@proxy.net:1080

# URL without credentials
print(proxy.to_url(exclude_credentials=True))
# socks5h://proxy.net:1080

# Base protocol scheme without socks4a/socks5h extension
print(proxy.to_url(socks_ext=False))
# socks5://user:pass@proxy.net:1080

# Available via properties
print(proxy.url)
print(proxy.origin)  # Excludes credentials
print(str(proxy))
```

#### Formatted String Output

Serialize a `ProxyServer` into any supported text format:

```python
from proxy_string import ProxyServer, ProxyStringFormat

proxy = ProxyServer(
    host="192.168.1.1",
    port=8080,
    username="myuser",
    password="mypassword",
)

# Export to a specific format
text = proxy.to_string(ProxyStringFormat.USER_PASS_AT_HOST_PORT)
print(text)
# myuser:mypassword@192.168.1.1:8080

# Auto-format (defaults to HOST_PORT_USER_PASS if credentials exist, otherwise HOST_PORT)
text = proxy.to_string()
print(text)
# 192.168.1.1:8080:myuser:mypassword
```

#### Dictionary and JSON

```python
proxy = ProxyServer.from_url("http://admin:secret@proxy.com:8080")

# Dictionary
d = proxy.to_dict()
# {'host': 'proxy.com', 'port': 8080, 'protocol': <ProxyServerProtocol.HTTP: 'http'>, ...}

# JSON
json_str = proxy.to_json()

# Reconstruct from dictionary or JSON
p1 = ProxyServer.from_dict(d)
p2 = ProxyServer.from_json(json_str)
```

---

### Third-Party HTTP Client Preparation

Use `prepare_for()` to obtain library-ready proxy configurations:

```python
proxy = ProxyServer.from_url("http://user:pass@proxy.com:8080")

# requests & urllib
requests_proxies = proxy.prepare_for("requests")
# {'http': 'http://user:pass@proxy.com:8080', 'https': 'http://user:pass@proxy.com:8080'}

# httpx, httpx2, aiohttp, urllib3, pycurl, curl_cffi
httpx_proxy = proxy.prepare_for("httpx")
# 'http://user:pass@proxy.com:8080'

# SupportedPackage Literal type provides IDE autocomplete and static type safety
from proxy_string import SupportedPackage

target_pkg: SupportedPackage = "httpx2"
httpx2_proxy = proxy.prepare_for(target_pkg)

# playwright
playwright_proxy = proxy.prepare_for("playwright")
# {'server': 'http://proxy.com:8080', 'username': 'user', 'password': 'pass'}
```

---

### Modifying Instances (`with_*` Methods)

Because `ProxyServer` objects are immutable, use `with_*` methods to create updated copies:

```python
proxy = ProxyServer(host="proxy.com", port=8080)

# Evolve individual attributes
p2 = proxy.with_port(9090)
p3 = proxy.with_creds("admin", "secret")
p4 = proxy.with_remote_dns(True)
```

---

### Internationalized Domain Names (IDN / Punycode)

Non-ASCII domain names are converted to Punycode ASCII for standard network compatibility, while the original Unicode domain remains accessible:

```python
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("https://代理服务器.中国")

print(proxy.host)
# xn--mnq04g52d6ywo0o.xn--fiqs8s

print(proxy.unicode_host)
# 代理服务器.中国

print(proxy.unicode_url)
# https://代理服务器.中国:443
```

---

### IPv6 Support

IPv6 addresses can be passed with or without square brackets. The parser normalizes them into RFC-compliant bracketed URLs:

```python
from proxy_string import ProxyServer

# With square brackets
p1 = ProxyServer.from_string("[2001:db8::1]:8080")
print(p1.host)  # '2001:db8::1'
print(p1.to_url())  # 'http://[2001:db8::1]:8080'

# Unbracketed
p2 = ProxyServer(host="2001:db8::1", port=8080)
print(p2.to_url())  # 'http://[2001:db8::1]:8080'
```

---

## API Reference

### `ProxyServer`

#### Attributes & Properties
- `host: str` — Hostname or IP address (Punycode-encoded for IDN).
- `port: int` — Port number (`0..65535`). Defaults to protocol standard if omitted (80, 443, 1080).
- `protocol: ProxyServerProtocol` — Protocol (`HTTP`, `HTTPS`, `SOCKS4`, `SOCKS5`).
- `username: str | None` — Authentication username.
- `password: str | None` — Authentication password (distinguishes empty password `""` from `None`).
- `remote_dns: bool | None` — Whether DNS is resolved on the proxy server (SOCKS only).
- `unicode_host: str` — Unicode representation of the hostname (for IDN).
- `host_value_type: HostValueType` — Host classification (`HostValueType.HOSTNAME`, `HostValueType.IPV4`, or `HostValueType.IPV6`).
- `host_ip_address: IPv4Address | IPv6Address | None` — Parsed IP address object if `host` is an IP.
- `url: str` — Complete URL representation.
- `origin: str` — URL representation excluding credentials.
- `unicode_url: str` — URL representation with Unicode host.
- `is_authenticated: bool` — `True` if credentials (`username` or `password`) are set.
- `is_socks: bool` — `True` if protocol is a SOCKS variant (`SOCKS4` or `SOCKS5`).
- `is_ssl: bool` — `True` if proxy connection uses TLS/SSL (`HTTPS`).

#### Class Methods
- `from_url(url: str) -> ProxyServer`
- `from_string(proxy_string: str, *, string_format: ProxyStringFormat | None = None, protocol: ProxyServerProtocol | None = None) -> ProxyServer`
- `from_file(input_file: str | Path, *, string_format: ProxyStringFormat | None = None, protocol: ProxyServerProtocol | None = None, encoding: str = "utf-8", encoding_errors: str = "strict", ignore_invalid: bool = False) -> Generator[ProxyServer, None, None]`
- `from_file_async(input_file: str | Path, *, string_format: ProxyStringFormat | None = None, protocol: ProxyServerProtocol | None = None, encoding: str = "utf-8", encoding_errors: str = "strict", ignore_invalid: bool = False) -> AsyncGenerator[ProxyServer, None]`
- `from_dict(input_dict: Mapping[str, Any]) -> ProxyServer`
- `from_json(input_json: str) -> ProxyServer`

#### Methods
- `to_url(socks_ext: bool = True, exclude_credentials: bool = False) -> str`
- `to_string(string_format: ProxyStringFormat | None = None) -> str`
- `to_dict() -> dict[str, Any]`
- `to_json() -> str`
- `with_host(host: str) -> ProxyServer`
- `with_port(port: int) -> ProxyServer`
- `with_protocol(protocol: ProxyServerProtocol | str) -> ProxyServer`
- `with_username(username: str | None) -> ProxyServer`
- `with_password(password: str | None) -> ProxyServer`
- `with_creds(username: str | None, password: str | None) -> ProxyServer`
- `with_remote_dns(remote_dns: bool | None) -> ProxyServer`
- `prepare_for(package_name: SupportedPackage) -> dict[str, Any] | str`

---

### Enumerations and Types

- **`ProxyServerProtocol`**: `HTTP = "http"`, `HTTPS = "https"`, `SOCKS4 = "socks4"`, `SOCKS5 = "socks5"`
- **`ProxyStringFormat`** (`StrEnum`): `URL = "url"`, `HOST_PORT = "host:port"`, `USER_PASS_HOST_PORT = "user:pass:host:port"`, `USER_PASS_AT_HOST_PORT = "user:pass@host:port"`, `HOST_PORT_USER_PASS = "host:port:user:pass"`, `HOST_PORT_AT_USER_PASS = "host:port@user:pass"`
- **`HostValueType`**: `HOSTNAME = "hostname"`, `IPV4 = "ipv4"`, `IPV6 = "ipv6"`
- **`SupportedPackage`**: `Literal["aiohttp", "curl_cffi", "httpx", "httpx2", "playwright", "pycurl", "requests", "urllib", "urllib3"]`

---

### Exceptions

All custom exceptions inherit from `ProxyStringError` and provide structured attributes for programmatic inspection:

- `ProxyStringError` — Base exception class for all `proxy-string` errors.
- `InvalidProxyStringError` — Raised when a proxy string is malformed or cannot be parsed (stores `e.proxy_string`).
- `InvalidProxyURLError` — Raised when a proxy URL is malformed, lacks an absolute scheme or host, or uses an unsupported scheme (stores `e.url`).
- `ProxyConfigurationError` — Base exception for proxy configuration and protocol constraint errors.
- `ProtocolConstraintError` — Raised when protocol network constraints are violated, such as SOCKS4 with IPv6 or HTTP with remote DNS resolution (stores `e.protocol`, `e.host`).
- `UnsupportedPackageError` — Raised when an unsupported client library is passed to `prepare_for()` (stores `e.package_name`).
- `ProtocolNotSupportedError` — Raised when a proxy protocol is incompatible with the target client library in `prepare_for()` (stores `e.package_name`, `e.protocol`).

```python
from proxy_string import (
    InvalidProxyStringError,
    InvalidProxyURLError,
    ProtocolConstraintError,
    ProxyServer,
    ProxyStringError,
)

try:
    proxy = ProxyServer.from_string("invalid:format:extra:fields:123")
except InvalidProxyStringError as e:
    print(f"String parsing error for '{e.proxy_string}': {e}")

try:
    proxy = ProxyServer(host="2001:db8::1", protocol="socks4")
except ProtocolConstraintError as e:
    print(f"Constraint violated for {e.protocol} on host {e.host}: {e}")

try:
    proxy = ProxyServer.from_url("ftp://proxy.com:8080")
except InvalidProxyURLError as e:
    print(f"URL error for '{e.url}': {e}")
except ProxyStringError as e:
    print(f"General proxy error: {e}")
```

---

## Development

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/)

```bash
# Clone the repository
git clone https://github.com/sergey-scat/proxy-string.git
cd proxy-string

# Install dependencies including optional backends
uv sync --all-extras

# Run the test suite with coverage
uv run pytest

# Check code formatting and lints
uv run ruff check
uv run ruff format --check

# Type check
uv run ty check src/proxy_string
```

---

## License

This project is licensed under the [MIT License](LICENSE).