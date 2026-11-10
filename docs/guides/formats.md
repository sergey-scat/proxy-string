# Supported String Formats

The `ProxyStringFormat` enumeration represents standard proxy text patterns used in public proxy lists, scraping tools, and proxies providers.

---

## Formats Table

| Enum Member | Pattern Format | Example | Description |
| :--- | :--- | :--- | :--- |
| `ProxyStringFormat.URL` | `scheme://[user:pass@]host:port` | `http://user:pass@proxy.com:8080` | Standard RFC/WHATWG URL string |
| `ProxyStringFormat.HOST_PORT` | `{host}:{port}` | `192.168.1.1:8080` | Anonymous or IP-whitelisted proxy |
| `ProxyStringFormat.USER_PASS_HOST_PORT` | `{username}:{password}:{host}:{port}` | `user:pass:192.168.1.1:8080` | Credentials prefix format |
| `ProxyStringFormat.USER_PASS_AT_HOST_PORT` | `{username}:{password}@{host}:{port}` | `user:pass@192.168.1.1:8080` | Credentials prefix with `@` |
| `ProxyStringFormat.HOST_PORT_USER_PASS` | `{host}:{port}:{username}:{password}` | `192.168.1.1:8080:user:pass` | Host and port prefix format |
| `ProxyStringFormat.HOST_PORT_AT_USER_PASS` | `{host}:{port}@{username}:{password}` | `192.168.1.1:8080@user:pass` | Host and port prefix with `@` |

---

## Automatic Format Detection

When calling `ProxyServer.from_string()` without specifying `string_format`, `proxy-string` evaluates the pattern dynamically:

1. **URL Scheme**: If the string contains `://`, it is parsed as a URL.
2. **At-Separator (`@`)**:
   - If the part before `@` contains `:` and the part after `@` contains a port number, it matches `USER_PASS_AT_HOST_PORT`.
   - If the part before `@` contains a host and port, it matches `HOST_PORT_AT_USER_PASS`.
3. **Single Colon (`:`)**:
   - Matches `HOST_PORT` (e.g. `1.2.3.4:8080` or `[::1]:8080`).
4. **Multiple Colons**:
   - Resolves IPv6 addresses with ports.
   - Evaluates 4-part sequences for `HOST_PORT_USER_PASS` vs `USER_PASS_HOST_PORT`.

---

## Handling Ambiguities

!!! warning "Ambiguity with Numeric Credentials"
    In 4-part colon-delimited formats (`HOST_PORT_USER_PASS` vs `USER_PASS_HOST_PORT`), if the username or password consists entirely of digits and falls into the valid port range (`0..65535`), automatic detection cannot guarantee which element is the port.

    ```python
    from proxy_string import ProxyServer, ProxyStringFormat

    # String where password "8080" looks like a port, or port "3128" looks like a password:
    raw_str = "192.168.1.1:8080:user:3128"

    # Explicitly pass the expected format to avoid ambiguity:
    proxy = ProxyServer.from_string(
        raw_str,
        string_format=ProxyStringFormat.HOST_PORT_USER_PASS,
    )
    ```

---

## Exporting to Formatted String

Use `proxy.to_string()` to convert a `ProxyServer` into any supported string format:

```python
from proxy_string import ProxyServer, ProxyStringFormat

proxy = ProxyServer(
    host="192.168.1.1",
    port=8080,
    username="alice",
    password="secret",
)

# Export to a specific format
print(proxy.to_string(ProxyStringFormat.USER_PASS_AT_HOST_PORT))
# alice:secret@192.168.1.1:8080

# Default auto-formatting:
# Outputs HOST_PORT_USER_PASS if credentials are present, otherwise HOST_PORT
print(proxy.to_string())
# 192.168.1.1:8080:alice:secret
```

