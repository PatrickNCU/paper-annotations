"""命令列入口。邏輯在 pa/probe.py；這一層只負責讓 `python probe.py` 找得到套件。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import probe

if __name__ == "__main__":
    sys.exit(probe.main(sys.argv))
