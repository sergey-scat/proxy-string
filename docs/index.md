---
title: Overview
description: Lightweight, type-safe Python library for parsing, validating, and converting proxy server connection data.
---

<p align="center">
  <img src="assets/logo.jpg" alt="proxy-string logo" width="220" />
</p>

# proxy-string

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff" /></a>
  <a href="https://github.com/bwhmather/ty"><img src="https://img.shields.io/badge/types-ty-blueviolet.svg" alt="Checked with ty" /></a>
  <a href="https://github.com/sergey-scat/proxy-string"><img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg" alt="Coverage" /></a>
</p>

A lightweight, type-safe Python library for parsing, validating, and converting proxy server connection data.

Supports **HTTP**, **HTTPS**, **SOCKS4**, and **SOCKS5** (including remote DNS schemes `socks4a` and `socks5h`), with full compatibility for **IPv4**, **IPv6**, **Unicode credentials**, and **IDN (Punycode)** hostnames.

---

## Key Features

- **WHATWG URL Standard Compliance**: URL parsing strictly adheres to modern WHATWG URL standards via `pywhatwgurl` (pure Python, installed by default), with optional high-performance C++ backends (`ada-url` and `can-ada`) selected automatically by speed priority.
- **Unicode & IDN Ready**:
    - Full support for UTF-8 Unicode usernames and passwords with percent-encoding.
    - Transparent conversion for internationalized domain names (e.g. `代理服务器.中国` ↔ `xn--mnq04g52d6ywo0o.xn--fiqs8s`).
- **Multi-Protocol Support**: Full support for HTTP, HTTPS, SOCKS4, and SOCKS5. Automatically maps `socks4a` and `socks5h` schemes to remote DNS resolution and enforces protocol constraints (such as SOCKS4 IPv6 network restrictions).
- **Flexible Parsing**:
    - Full URLs (e.g. `http://user:pass@192.168.1.1:8080`, `socks5h://...`).
    - Standard text formats (`host:port`, `user:pass:host:port`, `host:port@user:pass`, etc.) with automatic format detection.
    - Dictionaries (`from_dict`) and JSON strings (`from_json`).
    - Batch parsing from text files: synchronous (`from_file`) and asynchronous (`from_file_async`) generators with comment and whitespace filtering.
- **Immutable & Safe**: Data objects are frozen (`@attrs.frozen`), hashable, and comparable. Strict validation for ports (`0..65535`), protocols, and hostnames.
- **Evolution Methods**: Convenient `with_*` methods (`with_host`, `with_port`, `with_protocol`, `with_creds`, etc.) returning modified immutable copies.
- **Third-Party Client Integration**: Built-in `prepare_for()` method returning ready-to-use proxy configuration structures for `requests`, `httpx`, `httpx2`, `aiohttp`, `playwright`, `urllib`, `urllib3`, `pycurl`, and `curl_cffi`, strictly type-checked via `SupportedPackage` Literal.

---

## Quick Example

```python
from proxy_string import ProxyServer, ProxyServerProtocol

# Parse from URL
proxy = ProxyServer.from_url("socks5h://alice:secret@10.0.0.1:1080")
print(proxy.protocol)  # ProxyServerProtocol.SOCKS5
print(proxy.remote_dns)  # True

# Automatically detect text format
proxy2 = ProxyServer.from_string("proxy.example.com:8080:alice:secret")
print(proxy2.host)  # 'proxy.example.com'
print(proxy2.port)  # 8080

# Convert for use in requests or httpx
requests_cfg = proxy2.prepare_for("requests")
print(requests_cfg)
# {'http': 'http://alice:secret@proxy.example.com:8080', 'https': 'http://alice:secret@proxy.example.com:8080'}
```

---

## Next Steps

- Jump to [Installation](getting-started/installation.md) to set up `proxy-string` in your project.
- Follow the [Quickstart Guide](getting-started/quickstart.md) for step-by-step usage examples.
- Explore [Client Integrations](guides/integrations.md) to use proxies with `requests`, `httpx`, `playwright`, and more.
- Check the complete [API Reference](reference/proxy-server.md).
