#!/usr/bin/env python3
"""Refresh the vendored ARD spec schemas from ards-project/ard-spec.

Usage:
    python scripts/vendor_schemas.py [--ref main]

Downloads the canonical schema files into ``src/ardkit/schemas/`` so ardkit stays
pinned to a known spec revision. Review the resulting diff before committing.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/ards-project/ard-spec/{ref}/{path}"
FILES = {
    "spec/schemas/ai-catalog.schema.json": "ai-catalog.schema.json",
    "spec/schemas/ard.cddl": "ard.cddl",
    "spec/schemas/ard.openapi.yaml": "ard.openapi.yaml",
}
DEST = Path(__file__).resolve().parent.parent / "src" / "ardkit" / "schemas"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="main", help="git ref of ard-spec to vendor")
    args = parser.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    for src, name in FILES.items():
        url = RAW.format(ref=args.ref, path=src)
        print(f"fetch {url}")
        with urllib.request.urlopen(url) as resp:  # noqa: S310 - fixed trusted host
            data = resp.read()
        (DEST / name).write_bytes(data)
        print(f"  -> {name} ({len(data)} bytes)")
    print("done — review the diff and update SPEC_VERSION if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
