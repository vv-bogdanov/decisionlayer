from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEBUG_LOG_ENV = "REPO_DECISIONS_DEBUG_LOG"
RUN_ID_ENV = "REPO_DECISIONS_RUN_ID"


def log_event(event: dict[str, Any]) -> None:
    log_path = os.environ.get(DEBUG_LOG_ENV)
    if not log_path:
        return

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": os.environ.get(RUN_ID_ENV),
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        **event,
    }
    path = Path(log_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    data = path.read_bytes()
    return {
        "path": str(path),
        "exists": True,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
