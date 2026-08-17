"""命令列入口。邏輯在 pa/library.py。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import library

if __name__ == "__main__":
    raise SystemExit(library.main(sys.argv))
