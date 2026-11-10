# Parsing Sources

`proxy-string` provides rich factory methods to ingest proxy data from URLs, delimited strings, text files, dictionaries, and JSON payloads.

---

## URLs (`from_url`)

```python
from proxy_string import ProxyServer

# Parse full URL
proxy = ProxyServer.from_url("https://user:secret@proxy.domain.com:8443")

# Scheme without port defaults to standard protocol port (80, 443, 1080)
http_proxy = ProxyServer.from_url("http://proxy.domain.com")
print(http_proxy.port)  # 80
```

### Remote DNS (`socks4a` and `socks5h`)

When URL schemes `socks4a` or `socks5h` are passed:
- `protocol` is mapped to `ProxyServerProtocol.SOCKS4` or `ProxyServerProtocol.SOCKS5`.
- `remote_dns` flag is automatically set to `True`.

---

## Formatted Strings (`from_string`)

Parse common colon-separated or at-separated strings:

```python
from proxy_string import ProxyServer, ProxyServerProtocol, ProxyStringFormat

# Format detected automatically
p1 = ProxyServer.from_string("10.0.0.1:8080:admin:pass")

# With explicit protocol (default protocol is HTTP if unspecified)
p2 = ProxyServer.from_string(
    "10.0.0.1:1080",
    protocol=ProxyServerProtocol.SOCKS5,
)

# With explicit format pattern
p3 = ProxyServer.from_string(
    "admin:pass@10.0.0.1:8080",
    string_format=ProxyStringFormat.USER_PASS_AT_HOST_PORT,
)
```

---

## Text Files (`from_file` and `from_file_async`)

Large lists of proxies stored in text files (e.g. proxy pool lists) can be parsed using memory-efficient generators.

Text files may contain:
- Blank lines and whitespace (automatically skipped).
- Comments starting with `#` (automatically stripped).

### Synchronous Reading

```python
from proxy_string import ProxyServer, ProxyServerProtocol

# Stream proxies line by line
for proxy in ProxyServer.from_file(
    "proxies.txt",
    protocol=ProxyServerProtocol.HTTPS,
    ignore_invalid=True,  # Silently skip malformed lines
):
    print(proxy.to_url())
```

### Asynchronous Reading (`from_file_async`)

Async generators allow non-blocking file streaming in asyncio loops:

```python
import asyncio
from proxy_string import ProxyServer, ProxyServerProtocol


async def process_proxies():
    async for proxy in ProxyServer.from_file_async(
        "proxies.txt",
        protocol=ProxyServerProtocol.SOCKS5,
        ignore_invalid=True,
    ):
        print(f"Loaded: {proxy.host}:{proxy.port}")


asyncio.run(process_proxies())
```

---

## Dictionaries and JSON (`from_dict` and `from_json`)

Convert between Python mappings, JSON strings, and `ProxyServer` instances:

```python
from proxy_string import ProxyServer

data = {
    "host": "192.168.1.1",
    "port": 8080,
    "protocol": "http",
    "username": "user",
    "password": "pwd",
    "remote_dns": False,
}

# From dictionary
proxy = ProxyServer.from_dict(data)

# To JSON string
json_data = proxy.to_json()

# From JSON string
restored_proxy = ProxyServer.from_json(json_data)
assert proxy == restored_proxy
```

---

## IPv6 and IDN Hostnames

### IPv6 Normalization

IPv6 addresses can be supplied bracketed or unbracketed:

```python
from proxy_string import ProxyServer

p1 = ProxyServer.from_string("[2001:db8::1]:8080")
p2 = ProxyServer(host="2001:db8::1", port=8080)

assert p1.host == "2001:db8::1"
assert p1.to_url() == "http://[2001:db8::1]:8080"
```

### Internationalized Domain Names (IDN)

Non-ASCII international domain names are converted to Punycode ASCII for standard network client compatibility:

```python
from proxy_string import ProxyServer

proxy = ProxyServer.from_url("https://代理服务器.中国")

print(proxy.host)  # 'xn--mnq04g52d6ywo0o.xn--fiqs8s'
print(proxy.unicode_host)  # '代理服务器.中国'
print(proxy.unicode_url)  # 'https://代理服务器.中国:443'
```
