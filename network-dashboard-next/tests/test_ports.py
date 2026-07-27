from app.core.ports import choose_port, port_is_available


def test_ephemeral_port_is_valid() -> None:
    port = choose_port(candidates=())
    assert 1 <= port <= 65535


def test_preferred_available_port() -> None:
    port = choose_port(candidates=())
    assert port_is_available(port)
    assert choose_port(preferred=port) == port
