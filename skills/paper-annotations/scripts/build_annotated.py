"""命令列入口。邏輯在 pa/annotate.py。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import annotate

if __name__ == "__main__":
    sys.exit(annotate.main(sys.argv))
