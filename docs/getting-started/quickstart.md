# Quickstart

This tutorial walks through creating, inspecting, and converting proxy server connections using `proxy-string`.

---

## Direct Initialization

You can instantiate `ProxyServer` directly by providing its attributes:

```python
from proxy_string import ProxyServer, ProxyServerProtocol

proxy = ProxyServer(
    host="proxy.example.com",
    port=8080,
    protocol=ProxyServerProtocol.HTTPS,
    username="alice",
    password="secret_password",
)

print(proxy)
# https://alice:secret_password@proxy.example.com:8080
```

### Unicode Credentials Support

Usernames and passwords containing Unicode characters are automatically percent-encoded when rendered as URLs:

```python
proxy = ProxyServer(
    host="proxy.example.com",
    port=8080,
    protocol=ProxyServerProtocol.HTTPS,
    username="юзер",
    password="пароль",
)

print(proxy.to_url())
# https://%D1%8E%D0%B7%D0%B5%D1%80:%D0%BF%D0%B0%D1%80%D0%BE%D0%BB%D1%8C@proxy.example.com:8080

# The original Unicode values remain untouched on the object attributes:
print(proxy.username)  # 'юзер'
print(proxy.password)  # 'пароль'
```

---

## Parsing from URL

Use `ProxyServer.from_url()` to parse standard proxy connection URLs:

```python
from proxy_string import ProxyServer, ProxyServerProtocol

# Parse standard HTTP proxy
p1 = ProxyServer.from_url("http://user:pass@192.168.1.1:8080")
print(p1.host)  # '192.168.1.1'
print(p1.port)  # 8080
print(p1.protocol)  # ProxyServerProtocol.HTTP

# SOCKS proxy with remote DNS resolution (socks5h scheme)
p2 = ProxyServer.from_url("socks5h://10.0.0.1:1080")
print(p2.protocol)  # ProxyServerProtocol.SOCKS5
print(p2.remote_dns)  # True
```

---

## Parsing from String (Auto-Detection)

Proxy lists frequently provide proxies in non-URL text formats like `host:port` or `host:port:user:pass`. Use `ProxyServer.from_string()`:

```python
from proxy_string import ProxyServer

# Automatically detected as HOST_PORT_USER_PASS
proxy = ProxyServer.from_string("192.168.1.100:8080:alice:password123")
print(proxy.host)  # '192.168.1.100'
print(proxy.port)  # 8080
print(proxy.username)  # 'alice'
print(proxy.password)  # 'password123'
```

---

## Inspecting Properties

`ProxyServer` provides convenient boolean flags and categorized properties:

```python
proxy = ProxyServer.from_url("socks5://alice:secret@192.168.1.1:1080")

# Security and protocol flags
print(proxy.is_authenticated)  # True
print(proxy.is_socks)  # True
print(proxy.is_ssl)  # False

# Host classification
print(proxy.host_value_type)  # HostValueType.IPV4
print(proxy.host_ip_address)  # IPv4Address('192.168.1.1')

# URLs with and without credentials
print(proxy.url)  # 'socks5://alice:secret@192.168.1.1:1080'
print(proxy.origin)  # 'socks5://192.168.1.1:1080'
```
