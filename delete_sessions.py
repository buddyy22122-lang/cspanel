#!/usr/bin/env python3
"""把指定的 Claude Code 会话移到废纸篓（Windows 上是回收站）。由面板上的「复制删除命令」生成调用。

用法：python3 delete_sessions.py <会话ID> [<会话ID> ...]    （Windows：python delete_sessions.py ...）
- 正在运行的会话不会删除
- 执行前列出要移走的文件，输入 y 才执行
- 只移到废纸篓/回收站，可以从里面放回原处
"""
import ctypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import build

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
EXTRA_DIRS = ("file-history", "session-env")


def session_paths(sid):
    """这个会话在 ~/.claude 下的全部文件和文件夹。"""
    paths = []
    for jsonl in build.PROJECTS_DIR.glob(f"*/{sid}.jsonl"):
        paths.append(jsonl)
        folder = jsonl.with_suffix("")
        if folder.is_dir():
            paths.append(folder)
    for name in EXTRA_DIRS:
        p = build.CLAUDE_DIR / name / sid
        if p.exists():
            paths.append(p)
    return paths


def describe(sid, paths):
    jsonl = next((p for p in paths if p.suffix == ".jsonl"), None)
    if not jsonl:
        return "（没有聊天记录文件）", ""
    s = build.read_session(str(jsonl))
    title = s["customTitle"] or s["aiTitle"] or s["firstPrompt"] or "（无标题）"
    return title, build.short_home(s["cwd"] or "")


TRASH_NAME = "回收站" if build.IS_WINDOWS else "废纸篓"


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("wFunc", ctypes.c_uint),
        ("pFrom", ctypes.c_wchar_p),
        ("pTo", ctypes.c_wchar_p),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", ctypes.c_int),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", ctypes.c_wchar_p),
    ]


def move_to_recycle_bin(paths):
    """Windows：用 Shell API 移到回收站（FO_DELETE + FOF_ALLOWUNDO），不依赖第三方包。"""
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = "\0".join(os.path.abspath(p) for p in paths) + "\0\0"  # 路径之间用 \0 分隔，末尾两个 \0
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if code or op.fAnyOperationsAborted:
        raise OSError(f"移到回收站失败（错误码 {code}）")


def move_to_trash(paths):
    if build.IS_WINDOWS:
        move_to_recycle_bin(paths)
        return
    if shutil.which("trash"):
        subprocess.run(["trash", *map(str, paths)], check=True)
        return
    # 旧版 macOS 没有 trash 命令，改用访达
    items = ", ".join(f'POSIX file "{p}"' for p in paths)
    subprocess.run(["osascript", "-e", f'tell application "Finder" to delete {{{items}}}'], check=True, stdout=subprocess.DEVNULL)


def main(args):
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not args:
        print(__doc__)
        return 1
    live = build.read_live_sessions()
    todo = []
    for sid in dict.fromkeys(a.strip().lower() for a in args):
        if not UUID_RE.match(sid):
            print(f"✗ 跳过：{sid} 不是合法的会话 ID")
            continue
        if sid in live:
            print(f"✗ 跳过：{sid[:8]}… 正在运行。先在那个终端窗口里退出 Claude，再删除。")
            continue
        paths = session_paths(sid)
        if not paths:
            print(f"✗ 跳过：{sid[:8]}… 找不到文件，可能已经删过了")
            continue
        todo.append((sid, paths))

    if not todo:
        print("\n没有可以删除的会话。")
        return 1

    print(f"\n将把下面 {len(todo)} 个会话移到废纸篓：\n")
    for sid, paths in todo:
        title, project = describe(sid, paths)
        print(f"● {title}")
        print(f"  项目：{project}")
        for p in paths:
            print(f"    {build.short_home(str(p))}{'/' if p.is_dir() else ''}")
        print()

    try:
        answer = input(f"确认移到{TRASH_NAME}吗？输入 y 回车确认，直接回车取消：").strip().lower()
    except EOFError:
        answer = ""
    if answer not in ("y", "yes", "是"):
        print("已取消，什么都没动。")
        return 1

    failed = 0
    for sid, paths in todo:
        try:
            move_to_trash(paths)
            print(f"✓ 已移到{TRASH_NAME}：{sid[:8]}…")
        except (subprocess.CalledProcessError, OSError) as e:
            failed += 1
            print(f"✗ 失败：{sid[:8]}… {e}")

    print("\n正在刷新面板数据…")
    build.main()
    refresh = "F5" if build.IS_WINDOWS else "⌘R"
    restore = "还原" if build.IS_WINDOWS else "放回原处"
    print(f"刷新浏览器里的面板（{refresh}）就能看到变化。删错了可以去{TRASH_NAME}里「{restore}」。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
