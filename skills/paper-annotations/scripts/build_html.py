"""命令列入口。邏輯在 pa/page.py；頁面的樣式與腳本在 pa/assets/。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import page

if __name__ == "__main__":
    sys.exit(page.main(sys.argv))
