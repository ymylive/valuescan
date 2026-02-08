#!/usr/bin/env python3
import json
import socket
import subprocess
from pathlib import Path

_redir_path = Path("/etc/valuescan_clash_redir_port")
try:
    REDIR_PORT = int(_redir_path.read_text().strip()) if _redir_path.exists() else 7892
except Exception:
    REDIR_PORT = 7892
NODES_PATH = Path("/root/valuescan/api/data/clash_nodes.json")


def _run(cmd) -> int:
    result = subprocess.run(cmd, check=False)
    return result.returncode


def _resolve_ipv4(host: str):
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
    except Exception:
        return set()
    return {info[4][0] for info in infos}


def _load_proxy_targets():
    if not NODES_PATH.exists():
        return {}
    try:
        nodes = json.loads(NODES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    targets = {}
    for node in nodes:
        server = node.get("server")
        port = node.get("port")
        if not server or not isinstance(port, int):
            continue
        targets.setdefault(server, set()).add(port)
    return targets


def main() -> None:
    _run(["iptables", "-t", "nat", "-N", "CLASH_OUTPUT"])
    _run(["iptables", "-t", "nat", "-F", "CLASH_OUTPUT"])

    for cidr in [
        "0.0.0.0/8",
        "10.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "100.64.0.0/10",
    ]:
        _run(["iptables", "-t", "nat", "-A", "CLASH_OUTPUT", "-d", cidr, "-j", "RETURN"])

    targets = _load_proxy_targets()
    for host, ports in targets.items():
        for ip in _resolve_ipv4(host):
            for port in sorted(ports):
                _run(
                    [
                        "iptables",
                        "-t",
                        "nat",
                        "-A",
                        "CLASH_OUTPUT",
                        "-p",
                        "tcp",
                        "-d",
                        ip,
                        "--dport",
                        str(port),
                        "-j",
                        "RETURN",
                    ]
                )

    _run(["iptables", "-t", "nat", "-A", "CLASH_OUTPUT", "-p", "tcp", "-j", "REDIRECT", "--to-ports", str(REDIR_PORT)])

    if _run(["iptables", "-t", "nat", "-C", "OUTPUT", "-p", "tcp", "-j", "CLASH_OUTPUT"]) != 0:
        _run(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "-j", "CLASH_OUTPUT"])


if __name__ == "__main__":
    main()
