"""命令列入口。邏輯在 pa/librarypage.py。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import librarypage

if __name__ == "__main__":
    raise SystemExit(librarypage.main(sys.argv))
