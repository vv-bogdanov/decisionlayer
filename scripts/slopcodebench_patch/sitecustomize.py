from __future__ import annotations

import os

if os.environ.get("MEMORYCORE_SLOPCODE_DECISION_LAYER") == "1":
    from memorycore_slopcodebench_patch import apply

    apply()
