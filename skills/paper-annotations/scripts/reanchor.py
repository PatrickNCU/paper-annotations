"""命令列入口。邏輯在 pa/reanchor.py。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import reanchor

if __name__ == "__main__":
    sys.exit(reanchor.main(sys.argv))
