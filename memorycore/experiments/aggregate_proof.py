from __future__ import annotations

import sys
from pathlib import Path

from memorycore.reporting.proof import write_proof_index


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path("reports/proof")
    index_path = write_proof_index(root)
    print(index_path)


if __name__ == "__main__":
    main()
