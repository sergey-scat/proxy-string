# Third-Party Client Integrations

The `prepare_for()` method converts a `ProxyServer` instance into the exact configuration structure expected by Python's most popular HTTP clients and browser automation frameworks.

---

## Supported Libraries

The `SupportedPackage` type alias defines all supported client names:

```python
from proxy_string import SupportedPackage

# Type Literal: "aiohttp" | "curl_cffi" | "httpx" | "httpx2" | "playwright" | "pycurl" | "requests" | "urllib" | "urllib3"
```

---

## Integration Recipes

### `requests` & `urllib`

`requests` and standard library `urllib` expect a dictionary mapping URL schemes to proxy URLs:

```python
import requests
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("http://user:secret@192.168.1.1:8080")
proxies_dict = proxy.prepare_for("requests")
# {'http': 'http://user:secret@192.168.1.1:8080', 'https': 'http://user:secret@192.168.1.1:8080'}

response = requests.get("https://httpbin.org/ip", proxies=proxies_dict)
print(response.json())
```

---

### `httpx` & `httpx2`

`httpx` takes a proxy URL string for its `proxy` parameter:

```python
import httpx
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("http://user:secret@192.168.1.1:8080")
proxy_url = proxy.prepare_for("httpx")
# 'http://user:secret@192.168.1.1:8080'

client = httpx.Client(proxy=proxy_url)
response = client.get("https://httpbin.org/ip")
print(response.json())
```

---

### `aiohttp`

`aiohttp` client sessions accept a proxy URL string:

```python
import aiohttp
import asyncio
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("http://user:secret@192.168.1.1:8080")
proxy_str = proxy.prepare_for("aiohttp")


async def fetch():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://httpbin.org/ip", proxy=proxy_str) as response:
            print(await response.json())


asyncio.run(fetch())
```

---

### `playwright`

Playwright requires a dictionary separating the proxy server host and port from credentials:

```python
from playwright.sync_api import sync_playwright
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("socks5://alice:password123@10.0.0.1:1080")
playwright_config = proxy.prepare_for("playwright")
# {'server': 'socks5://10.0.0.1:1080', 'username': 'alice', 'password': 'password123'}

with sync_playwright() as p:
    browser = p.chromium.launch(proxy=playwright_config)
    page = browser.new_page()
    page.goto("https://httpbin.org/ip")
    print(page.content())
    browser.close()
```

---

### `curl_cffi` & `pycurl`

```python
from curl_cffi import requests as curl_requests
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("http://user:secret@proxy.com:8080")
proxy_str = proxy.prepare_for("curl_cffi")

response = curl_requests.get("https://httpbin.org/ip", proxy=proxy_str)
print(response.text)
```

---

## Error Handling

If an unsupported package name or an incompatible protocol is passed, typed exceptions are raised:

```python
from proxy_string import (
    ProxyServer,
    UnsupportedPackageError,
    ProtocolNotSupportedError,
)

proxy = ProxyServer.from_url("socks4://192.168.1.1:1080")

# Unknown client name
try:
    proxy.prepare_for("unknown_lib")
except UnsupportedPackageError as e:
    print(f"Unknown package: {e.package_name}")

# Incompatible protocol
try:
    proxy.prepare_for("some_unsupported_protocol_lib")
except ProtocolNotSupportedError as e:
    print(f"Protocol {e.protocol} is not supported by {e.package_name}")
```
