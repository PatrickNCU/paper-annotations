"""命令列入口。邏輯在 pa/server.py。

啟動器（開啟複習頁.cmd）與 server 的重建子行程都指著這個檔案的路徑，
搬動或改名前先看 pa/server.py 裡的 SCRIPTS。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pa import server

if __name__ == "__main__":
    sys.exit(server.main(sys.argv))
