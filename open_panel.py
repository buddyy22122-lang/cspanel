#!/usr/bin/env python3
"""用 Chrome/Edge 的独立窗口（无地址栏、无标签页）打开 dashboard.html。由 start.bat 调用。

URL 在这里生成并直接传给浏览器，不经过批处理：
中文路径会被编码成 %E4%BC%9A… ，批处理会把 %… 当成变量吞掉，地址就坏了。
"""
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILE = HERE / "dashboard.html"


def find_browser():
    roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData")]
    candidates = [r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"]
    for rel in candidates:
        for root in filter(None, roots):
            path = Path(root) / rel
            if path.is_file():
                return str(path)
    return None


def main():
    if not FILE.is_file():
        print("dashboard.html 不存在，请先运行 build.py")
        return 1
    url = FILE.as_uri()
    browser = find_browser()
    if browser:
        subprocess.Popen([browser, f"--app={url}"])
    else:
        webbrowser.open(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
