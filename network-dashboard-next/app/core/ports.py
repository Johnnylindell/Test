from __future__ import annotations

import socket
from collections.abc import Iterable


DEFAULT_CANDIDATES = (8793, 8794, 8795, 8800, 8801, 8810)


def port_is_available(port: int, host: str = "127.0.0.1") -> bool:
    if not 1 <= port <= 65535:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(preferred: int = 0, candidates: Iterable[int] = DEFAULT_CANDIDATES) -> int:
    if preferred:
        if not port_is_available(preferred):
            raise RuntimeError(f"Den konfigurerade porten {preferred} är upptagen.")
        return preferred

    for candidate in candidates:
        if port_is_available(candidate):
            return candidate

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
