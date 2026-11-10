# Modifying Proxies (`with_*` Methods)

`ProxyServer` instances are strictly **immutable** and **frozen** (`@attrs.frozen`).

---

## Why Immutability?

1. **Thread Safety**: Safe to share across threads or asynchronous coroutines without locking.
2. **Hashable**: `ProxyServer` instances can be placed into Python `set` collections (e.g. deduplicating proxy lists) or used as dictionary keys.
3. **Predictability**: Objects cannot be mutated unexpectedly by helper functions or client libraries.

```python
from proxy_string import ProxyServer

proxy = ProxyServer(host="proxy.com", port=8080)

# Attribute assignment raises FrozenInstanceError
try:
    proxy.port = 9090
except Exception as e:
    print(type(e).__name__)  # FrozenInstanceError
```

---

## Evolution Methods (`with_*`)

To create a modified copy of an existing proxy, use the `with_*` methods. Each method returns a **new** validated `ProxyServer` instance while leaving the original instance unchanged:

```python
from proxy_string import ProxyServer, ProxyServerProtocol

proxy = ProxyServer(host="proxy.example.com", port=8080)

# Modify port
p2 = proxy.with_port(9090)

# Modify credentials
p3 = p2.with_creds("admin", "new_secret")

# Modify protocol
p4 = p3.with_protocol(ProxyServerProtocol.HTTPS)

# Modify remote DNS resolution
p5 = p4.with_protocol("socks5").with_remote_dns(True)
```

### Available Evolution Methods

| Method | Description |
| :--- | :--- |
| `with_host(host: str)` | Changes the host and recalculates host type and IDN encoding |
| `with_port(port: int)` | Validates and changes the port (`0..65535`) |
| `with_protocol(protocol: ProxyServerProtocol \| str)` | Changes the protocol and validates protocol compatibility |
| `with_username(username: str \| None)` | Updates the username |
| `with_password(password: str \| None)` | Updates the password |
| `with_creds(username: str \| None, password: str \| None)` | Atomically updates both username and password |
| `with_remote_dns(remote_dns: bool \| None)` | Updates the remote DNS resolution setting (SOCKS protocols) |

---

## Method Chaining

Because every `with_*` method returns a `ProxyServer`, you can chain multiple updates cleanly:

```python
updated = (
    proxy.with_host("fallback.example.com")
    .with_port(1080)
    .with_protocol("socks5")
    .with_remote_dns(True)
    .with_creds("worker", "token123")
)
```

All validation rules (e.g. valid port ranges, protocol constraints, IPv6 formatting) are executed on each step, ensuring an invalid proxy object can never be created.

