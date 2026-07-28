from __future__ import annotations

import os

# Keep the test process deterministic even when pytest is started from an
# installation shell that already contains production/parallel environment
# variables. Individual tests can still replace app.main.settings explicitly.
os.environ["COOKIE_SECURE"] = "false"
os.environ["DASHBOARD_READ_ONLY"] = "false"
os.environ["EXTERNAL_SIDE_EFFECTS"] = "false"
os.environ["NOTIFICATION_SCHEDULER_ENABLED"] = "false"
os.environ["PORT"] = "0"
