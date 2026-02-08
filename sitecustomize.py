import os
import socket


def _force_ipv4() -> None:
    if os.getenv("NOFX_FORCE_IPV4", "1").lower() not in ("1", "true", "yes", "on"):
        return
    try:
        import urllib3.util.connection as urllib3_cn
        urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
    except Exception:
        pass


_force_ipv4()
