from __future__ import annotations

import uvicorn

from app.main import app, selected_port


if __name__ == "__main__":
    port = selected_port()
    print(f"Network Dashboard Next kör på http://localhost:{port}", flush=True)
    uvicorn.run(app, host=app.state.settings.host, port=port, log_level="info")
