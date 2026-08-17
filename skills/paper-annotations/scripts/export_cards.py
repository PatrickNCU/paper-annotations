"""命令列入口。邏輯在 pa/export.py。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import export

if __name__ == "__main__":
    sys.exit(export.main(sys.argv))
