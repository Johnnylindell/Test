from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
from pathlib import Path

from scripts import readiness_report


def touch_required_static(root: Path) -> None:
    for relative in readiness_report.REQUIRED_STATIC:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")


def sqlite_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE example(id INTEGER PRIMARY KEY,value TEXT)")
        connection.execute("INSERT INTO example(value) VALUES('ok')")


def private_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


def arguments(tmp_path: Path, root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        root=str(root),
        origin="",
        live_origin="",
        database=str(tmp_path / "next.sqlite3"),
        live_database=str(tmp_path / "live.sqlite3"),
        env_file=str(tmp_path / "network-dashboard-next.env"),
        secrets=str(tmp_path / "integration-secrets.json"),
        google_token=str(tmp_path / "google-token.json"),
        google_client=str(tmp_path / "google-client.json"),
        legacy_report=str(tmp_path / "legacy-report.json"),
        service="network-dashboard-next.service",
    )


def mock_runtime(monkeypatch) -> None:
    monkeypatch.setattr(readiness_report, "_service_state", lambda service: (True, "active"))
    monkeypatch.setattr(
        readiness_report,
        "_migration_state",
        lambda database, directory: (True, "total=11 pending=0 checksum_mismatches=none"),
    )


def test_ready_report_accepts_isolated_secure_setup(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "app"
    touch_required_static(root)
    args = arguments(tmp_path, root)
    sqlite_database(Path(args.database))
    sqlite_database(Path(args.live_database))
    private_file(
        Path(args.env_file),
        "\n".join([
            f"DASHBOARD_DB_PATH={args.database}",
            "DASHBOARD_READ_ONLY=true",
            "EXTERNAL_SIDE_EFFECTS=false",
            "HOMELAB_ADMIN_PASSWORD=admin-password-123456",
            "PRESENCE_HASH_SECRET=" + "a" * 64,
            "PRESENCE_INGEST_TOKEN=" + "b" * 64,
            "ASSISTANT_SIGNING_SECRET=" + "c" * 64,
            f"INTEGRATION_SECRETS_PATH={args.secrets}",
        ]) + "\n",
    )
    secret_value = "home-assistant-secret-token-123456789"
    private_file(
        Path(args.secrets),
        json.dumps({
            "format": "network-dashboard-integration-secrets-v1",
            "values": {"home_assistant_token": secret_value},
        }),
    )
    private_file(
        Path(args.legacy_report),
        json.dumps({"ok": True, "adopted": ["home_assistant_token"], "sensitive_values_exposed": False}),
    )
    mock_runtime(monkeypatch)

    report = readiness_report.build_report(args)
    assert report["ok"] is True
    assert report["status"] == "ready"
    assert report["failed_critical"] == []
    assert secret_value not in json.dumps(report)
    assert "google.token" in report["warnings"]
    assert "google.client" in report["warnings"]
    assert "credential.home_assistant_url" in report["warnings"]
    assert "credential.home_assistant_token" not in report["warnings"]


def test_report_blocks_live_database_reuse_and_secret_leak(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "app"
    touch_required_static(root)
    args = arguments(tmp_path, root)
    shared = tmp_path / "shared.sqlite3"
    args.database = str(shared)
    args.live_database = str(shared)
    sqlite_database(shared)
    private_file(
        Path(args.env_file),
        "\n".join([
            f"DASHBOARD_DB_PATH={shared}",
            "DASHBOARD_READ_ONLY=true",
            "EXTERNAL_SIDE_EFFECTS=false",
            "HOMELAB_ADMIN_PASSWORD=admin-password-123456",
            "PRESENCE_HASH_SECRET=" + "a" * 64,
            "PRESENCE_INGEST_TOKEN=" + "b" * 64,
            "ASSISTANT_SIGNING_SECRET=" + "c" * 64,
            f"INTEGRATION_SECRETS_PATH={args.secrets}",
        ]) + "\n",
    )
    secret_value = "leaked-home-assistant-token-123456"
    private_file(
        Path(args.secrets),
        json.dumps({
            "format": "network-dashboard-integration-secrets-v1",
            "values": {"home_assistant_token": secret_value},
        }),
    )
    private_file(
        Path(args.legacy_report),
        json.dumps({
            "ok": True,
            "debug": secret_value,
            "sensitive_values_exposed": False,
        }),
    )
    mock_runtime(monkeypatch)

    report = readiness_report.build_report(args)
    assert report["ok"] is False
    assert "database.isolated" in report["failed_critical"]
    assert "legacy.report_no_secret_values" in report["failed_critical"]


def test_migration_failure_blocks_readiness(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "app"
    touch_required_static(root)
    args = arguments(tmp_path, root)
    sqlite_database(Path(args.database))
    sqlite_database(Path(args.live_database))
    private_file(
        Path(args.env_file),
        "\n".join([
            f"DASHBOARD_DB_PATH={args.database}",
            "DASHBOARD_READ_ONLY=true",
            "EXTERNAL_SIDE_EFFECTS=false",
            "HOMELAB_ADMIN_PASSWORD=admin-password-123456",
            "PRESENCE_HASH_SECRET=" + "a" * 64,
            "PRESENCE_INGEST_TOKEN=" + "b" * 64,
            "ASSISTANT_SIGNING_SECRET=" + "c" * 64,
        ]) + "\n",
    )
    monkeypatch.setattr(readiness_report, "_service_state", lambda service: (True, "active"))
    monkeypatch.setattr(
        readiness_report,
        "_migration_state",
        lambda database, directory: (False, "total=11 pending=1 checksum_mismatches=none"),
    )
    report = readiness_report.build_report(args)
    assert report["ok"] is False
    assert "database.migrations" in report["failed_critical"]


def test_private_file_helper_sets_expected_mode(tmp_path: Path) -> None:
    path = tmp_path / "private.json"
    private_file(path, "{}")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
