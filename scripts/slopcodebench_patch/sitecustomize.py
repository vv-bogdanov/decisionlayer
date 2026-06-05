from __future__ import annotations

import os

if os.environ.get("MEMORYCORE_SLOPCODE_DECISION_LAYER") == "1":
    try:
        from memorycore_slopcodebench_patch import apply
        apply()
    except ModuleNotFoundError as exc:
        if exc.name != "slop_code":
            raise
