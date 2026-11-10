# Installation

`proxy-string` requires Python **3.12** or newer.

---

## Basic Installation

Install the library using your package manager of choice:

=== "uv (Recommended)"

    ```bash
    uv add proxy-string
    ```

=== "pip"

    ```bash
    pip install proxy-string
    ```

By default, `proxy-string` includes `pywhatwgurl` (a pure Python WHATWG URL compliant parser), allowing the package to install effortlessly in any environment without requiring a C++ compiler.

---

## Optional High-Speed Backends

For maximum URL parsing throughput (e.g. in high-load scrapers or proxy pool verifiers), install optional C++ WHATWG URL parsing engines:

=== "uv"

    ```bash
    # Install with can-ada (fastest)
    uv add "proxy-string[can_ada]"

    # Or install with ada-url
    uv add "proxy-string[ada_url]"
    ```

=== "pip"

    ```bash
    # Install with can-ada (fastest)
    pip install "proxy-string[can_ada]"

    # Or install with ada-url
    pip install "proxy-string[ada_url]"
    ```

### Backend Priority

When URL parsing is invoked, `proxy-string` checks available engines and automatically selects the fastest installed backend in the following order:

1. **`can-ada`** (C++ Ada URL binding, fastest)
2. **`ada-url`** (C++ Ada URL binding)
3. **`pywhatwgurl`** (Pure Python fallback, default)

You can check which backend is currently active at runtime:

```python
from proxy_string.whatwg_url import BACKEND_NAME

print(f"Active WHATWG URL backend: {BACKEND_NAME}")
```

