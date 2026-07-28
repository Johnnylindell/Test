from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_all_shell_scripts_parse_with_bash() -> None:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash is not installed")
    scripts = sorted((ROOT / "scripts").glob("*.sh"))
    assert scripts, "No shell scripts found"
    failures = []
    for script in scripts:
        result = run([bash, "-n", str(script)])
        if result.returncode:
            failures.append(f"{script.name}: {result.stderr or result.stdout}")
    assert failures == []


def test_all_javascript_files_parse_when_node_is_available() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    scripts = sorted((ROOT / "static").rglob("*.js"))
    assert scripts, "No JavaScript files found"
    failures = []
    for script in scripts:
        result = run([node, "--check", str(script)])
        if result.returncode:
            failures.append(f"{script.relative_to(ROOT)}: {result.stderr or result.stdout}")
    assert failures == []


def test_project_json_files_are_valid() -> None:
    files = [
        ROOT / "docs" / "parity.json",
        ROOT / "static" / "live" / "manifest.webmanifest",
    ]
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
