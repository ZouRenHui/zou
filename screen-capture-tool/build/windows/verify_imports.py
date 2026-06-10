"""Pre-build import check (ASCII-only output for Windows CI cp1252 console)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    for name in (
        "clipboard_utils",
        "record_button",
        "recorder",
        "screenshot",
        "screen_capture_gui",
    ):
        __import__(name)
    print("imports ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
