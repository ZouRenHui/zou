"""Pre-build import check (ASCII-only output for Windows CI cp1252 console)."""

from __future__ import annotations

import sys


def main() -> int:
    for name in ("image_processing", "image_utils", "ocr_engines", "image_tool_gui"):
        __import__(name)
    print("imports ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
