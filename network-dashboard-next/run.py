from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from app.main import app, selected_port


if __name__ == "__main__":
    port = selected_port()
    runtime_file = Path(os.getenv("DASHBOARD_RUNTIME_FILE", str(Path.home() / ".cache/network-dashboard-next/runtime.env")))
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(f"PORT={port}\nORIGIN=http://127.0.0.1:{port}\n", encoding="utf-8")
    print(f"Network Dashboard Next kör på http://localhost:{port}", flush=True)
    print(f"Runtime-information: {runtime_file}", flush=True)
    uvicorn.run(app, host=app.state.settings.host, port=port, log_level="info")
