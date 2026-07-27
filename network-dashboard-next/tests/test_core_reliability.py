from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.database.database import Database


def test_circuit_breaker_call_closes_after_success() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=0.1)
    assert breaker.call("service", lambda: "ok") == "ok"
    assert breaker.status("service")["failures"] == 0
    assert breaker.status("service")["open"] is False


def test_circuit_breaker_opens_and_allows_one_half_open_probe() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=0.1)

    def fail() -> None:
        raise RuntimeError("offline")

    with pytest.raises(RuntimeError):
        breaker.call("service", fail)
    with pytest.raises(RuntimeError):
        breaker.call("service", fail)
    assert breaker.status("service")["open"] is True
    with pytest.raises(CircuitOpenError):
        breaker.call("service", lambda: "blocked")

    time.sleep(0.12)
    assert breaker.call("service", lambda: "recovered") == "recovered"
    assert breaker.status("service")["open"] is False
    assert breaker.status("service")["failures"] == 0


def test_cache_can_store_none_without_reloading() -> None:
    cache = TTLCache()
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return None

    first, first_hit = cache.get_or_set("none", 10, loader)
    second, second_hit = cache.get_or_set("none", 10, loader)
    assert first is None
    assert second is None
    assert first_hit is False
    assert second_hit is True
    assert calls == 1
    assert cache.contains("none") is True


def test_cache_collapses_concurrent_loaders() -> None:
    cache = TTLCache()
    calls = 0
    results: list[tuple[str, bool]] = []
    barrier = threading.Barrier(5)
    lock = threading.Lock()

    def loader() -> str:
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.05)
        return "value"

    def worker() -> None:
        barrier.wait()
        results.append(cache.get_or_set("shared", 10, loader))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert calls == 1
    assert sorted(hit for _, hit in results) == [False, True, True, True, True]
    assert {value for value, _ in results} == {"value"}


def test_readonly_database_uri_handles_spaces_and_special_characters(tmp_path: Path) -> None:
    path = tmp_path / "budget #1 ?.sqlite3"
    database = Database(path)
    with database.transaction() as connection:
        connection.execute("CREATE TABLE example(id INTEGER PRIMARY KEY,value TEXT)")
        connection.execute("INSERT INTO example(value) VALUES('ok')")
    assert database.fetch_value("SELECT value FROM example") == "ok"
    assert "%23" in database._readonly_uri()
    assert "%3F" in database._readonly_uri()


def test_readonly_connection_rejects_writes(tmp_path: Path) -> None:
    database = Database(tmp_path / "readonly.sqlite3")
    with database.transaction() as connection:
        connection.execute("CREATE TABLE example(id INTEGER PRIMARY KEY,value TEXT)")
    with database.connection(readonly=True) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(Exception):
            connection.execute("INSERT INTO example(value) VALUES('blocked')")
