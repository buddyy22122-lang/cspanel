#!/usr/bin/env python3
"""扫描 ~/.claude 下的会话记录，生成 dashboard.html。

只读：不修改、不删除任何会话文件，也不联网。
用法：python3 build.py  然后打开 dashboard.html
"""
import ctypes
import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
LIVE_DIR = CLAUDE_DIR / "sessions"
IS_WINDOWS = os.name == "nt"


def norm_path(p):
    """统一成正斜杠、去掉末尾斜杠；Windows 路径不区分大小写，一并转小写，只用来比较。"""
    p = p.replace("\\", "/").rstrip("/")
    return p.lower() if IS_WINDOWS else p


HERE = Path(__file__).resolve().parent


def load_config():
    """读取可选的 config.json（已在 .gitignore 中），格式见 config.example.json。没有这个文件就全用默认值。"""
    path = HERE / "config.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"config.json 读取失败，已忽略：{e}", file=sys.stderr)
        return {}


def expand_path(p):
    """~ 展开成主目录，统一成正斜杠。"""
    return Path(p).expanduser().as_posix()


CONFIG = load_config()
# 单独成组的目录：路径在它下面的项目会放进「<groupName> 项目」分组；不配置就没有这个分组
GROUP_ROOT = expand_path(CONFIG["groupRoot"]) if CONFIG.get("groupRoot") else None
GROUP_NAME = CONFIG.get("groupName") or (Path(GROUP_ROOT).name if GROUP_ROOT else "")
# 文件夹改名后，旧会话记录里的路径还是旧名字；写「旧路径 → 新路径」，面板里就合并成一个项目
RENAMED = {expand_path(k): expand_path(v) for k, v in (CONFIG.get("renamed") or {}).items()}
RENAMED_NORM = {norm_path(k): v for k, v in RENAMED.items()}


def in_group(cwd):
    root = norm_path(GROUP_ROOT) if GROUP_ROOT else None
    return bool(root) and (norm_path(cwd) == root or norm_path(cwd).startswith(root + "/"))

TEMPLATE = HERE / "template.html"
OUTPUT = HERE / "dashboard.html"

TEXT_LIMIT = 4000          # 对话记录里单条消息最多保留的字数
TOOL_SUMMARY_LIMIT = 160   # 工具调用摘要的字数
FILE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone()
    except (AttributeError, ValueError):
        return None


def clip(text, limit):
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def human_prompt_text(rec):
    """如果这条记录是用户亲手输入的提问，返回文本；否则返回 None。"""
    if rec.get("type") != "user" or rec.get("isMeta") or rec.get("isSidechain"):
        return None
    if rec.get("toolUseResult") is not None:
        return None
    origin = rec.get("turnOrigin") or (rec.get("origin") or {}).get("kind")
    if origin and origin != "human":
        return None
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            return None
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text or text.startswith("<"):
        return None
    return text


def tool_summary(block):
    """把一次工具调用压缩成一行人能看懂的摘要。"""
    name = block.get("name") or "工具"
    inp = block.get("input") or {}
    detail = (
        inp.get("description")
        or inp.get("command")
        or inp.get("file_path")
        or inp.get("pattern")
        or inp.get("url")
        or inp.get("query")
        or inp.get("prompt")
        or inp.get("skill")
        or ""
    )
    if isinstance(detail, str):
        detail = short_home(detail) if norm_path(detail).startswith(norm_path(Path.home().as_posix()) + "/") else detail
    return name, clip(str(detail).replace("\n", " "), TOOL_SUMMARY_LIMIT)


def _win_process_start(pid):
    """Windows：进程还在运行就返回它的创建时间（FILETIME 整数），否则返回 None。"""
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        code = ctypes.c_ulong()
        if not k32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)) or code.value != 259:  # STILL_ACTIVE
            return None
        created, _a, _b, _c = (ctypes.c_ulonglong() for _ in range(4))
        if not k32.GetProcessTimes(ctypes.c_void_p(handle), *map(ctypes.byref, (created, _a, _b, _c))):
            return None
        return created.value
    finally:
        k32.CloseHandle(ctypes.c_void_p(handle))


def process_alive(info):
    """会话登记里的进程是否还活着。

    Windows 上 os.kill(pid, 0) 会向进程发控制台信号而不是探测，所以改用 OpenProcess；
    登记里有 procStart（进程创建时间）时一并比对，避免 PID 被别的进程复用而误判。
    """
    pid = int(info["pid"])
    if not IS_WINDOWS:
        os.kill(pid, 0)
        return True
    started = _win_process_start(pid)
    if started is None:
        return False
    recorded = info.get("procStart")
    return not (recorded and str(recorded).isdigit() and int(recorded) != started)


def read_live_sessions():
    """~/.claude/sessions/<pid>.json 登记着正在运行的窗口；进程不在了就不算。"""
    live = {}
    for path in glob.glob(str(LIVE_DIR / "*.json")):
        try:
            info = json.loads(Path(path).read_text(encoding="utf-8"))
            if not process_alive(info):
                continue
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        sid = info.get("sessionId")
        if sid:
            live[sid] = {"status": info.get("status") or "", "name": info.get("name") or ""}
    return live


def read_session(path):
    s = {
        "id": Path(path).stem,
        "cwd": None,
        "customTitle": None,
        "aiTitle": None,
        "firstPrompt": None,
        "prompts": [],          # 每次提问的时间（本地时间 ISO）
        "replies": 0,
        "models": Counter(),
        "tools": Counter(),
        "files": Counter(),
        "tokens": Counter(),
        "costUSD": None,
        "activeMs": 0,
        "start": None,
        "end": None,
        "entrypoint": None,
        "version": None,
        "gitBranch": None,
        "transcript": [],
    }
    seen_usage = set()
    seen_reply = set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("type")
            s["cwd"] = s["cwd"] or rec.get("cwd")
            s["entrypoint"] = s["entrypoint"] or rec.get("entrypoint")
            s["version"] = rec.get("version") or s["version"]
            if rec.get("gitBranch") and rec["gitBranch"] != "HEAD":
                s["gitBranch"] = rec["gitBranch"]

            if t == "custom-title" and rec.get("customTitle"):
                s["customTitle"] = rec["customTitle"]
                continue
            if t == "ai-title" and rec.get("aiTitle"):
                s["aiTitle"] = rec["aiTitle"]
                continue
            if t == "cost-state":
                cost = rec.get("totalCostUSD")
                if isinstance(cost, (int, float)) and cost > 0:
                    s["costUSD"] = max(s["costUSD"] or 0, cost)
                continue
            if t == "system" and rec.get("subtype") == "turn_duration":
                s["activeMs"] += rec.get("durationMs") or 0

            ts = parse_ts(rec.get("timestamp")) if rec.get("timestamp") else None
            if ts:
                s["start"] = min(s["start"] or ts, ts)
                s["end"] = max(s["end"] or ts, ts)
            ts_iso = ts.isoformat(timespec="minutes") if ts else None

            text = human_prompt_text(rec)
            if text is not None:
                s["firstPrompt"] = s["firstPrompt"] or clip(text, 120)
                if ts_iso:
                    s["prompts"].append(ts_iso)
                s["transcript"].append({"r": "u", "t": clip(text, TEXT_LIMIT), "ts": ts_iso})
                continue

            if t != "assistant" or rec.get("isSidechain"):
                continue
            msg = rec.get("message") or {}
            mid = msg.get("id") or rec.get("uuid")
            model = msg.get("model")
            if mid not in seen_reply:
                seen_reply.add(mid)
                s["replies"] += 1
                if model and not model.startswith("<"):
                    s["models"][model] += 1
            usage = msg.get("usage")
            if usage and mid not in seen_usage:
                seen_usage.add(mid)
                for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    s["tokens"][k] += usage.get(k) or 0
            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text", "").strip():
                    s["transcript"].append({"r": "a", "t": clip(block["text"], TEXT_LIMIT), "ts": ts_iso})
                elif block.get("type") == "tool_use":
                    name, detail = tool_summary(block)
                    s["tools"][name] += 1
                    fp = (block.get("input") or {}).get("file_path")
                    if name in FILE_TOOLS and fp:
                        s["files"][fp] += 1
                    s["transcript"].append({"r": "t", "n": name, "t": detail, "ts": ts_iso})

    if s["end"] is None:
        mtime = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).astimezone()
        s["start"] = s["end"] = mtime
    sub_dir = Path(path).with_suffix("") / "subagents"
    s["subagents"] = len(list(sub_dir.glob("*.jsonl"))) if sub_dir.is_dir() else 0
    return s


def short_home(p):
    """路径开头的主目录换成 ~，并统一用正斜杠（Windows 的反斜杠会让界面里切文件名出错）。"""
    p = p.replace("\\", "/")
    home = Path.home().as_posix()
    return "~" + p[len(home):] if norm_path(p).startswith(norm_path(home)) else p


def main():
    if not sys.stdout.isatty():  # 重定向到日志文件时统一用 UTF-8，免得 Windows 按 GBK 写出乱码
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    live = read_live_sessions()
    sessions = []
    for path in glob.glob(str(PROJECTS_DIR / "*" / "*.jsonl")):
        s = read_session(path)
        if not s["cwd"] or (not s["prompts"] and s["replies"] == 0):
            continue
        s["cwd"] = s["cwd"].replace("\\", "/")
        s["cwd"] = RENAMED_NORM.get(norm_path(s["cwd"]), s["cwd"])
        title = s["customTitle"] or s["aiTitle"] or s["firstPrompt"] or "（无标题）"
        tk = s["tokens"]
        sessions.append({
            "id": s["id"],
            "project": s["cwd"],
            "inGroup": in_group(s["cwd"]),
            "title": title,
            "firstPrompt": s["firstPrompt"] or "",
            "prompts": s["prompts"],
            "replies": s["replies"],
            "model": s["models"].most_common(1)[0][0] if s["models"] else "",
            "models": dict(s["models"]),
            "tools": dict(s["tools"]),
            "files": [short_home(f) for f, _ in s["files"].most_common()],
            "tokens": {
                "input": tk["input_tokens"],
                "output": tk["output_tokens"],
                "cacheRead": tk["cache_read_input_tokens"],
                "cacheWrite": tk["cache_creation_input_tokens"],
            },
            "costUSD": round(s["costUSD"], 4) if s["costUSD"] else None,
            "activeMs": s["activeMs"],
            "subagents": s["subagents"],
            "start": s["start"].isoformat(timespec="minutes"),
            "end": s["end"].isoformat(timespec="minutes"),
            "entrypoint": s["entrypoint"] or "",
            "version": s["version"] or "",
            "gitBranch": s["gitBranch"] or "",
            "live": live.get(s["id"]),
            "transcript": s["transcript"],
        })

    data = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "home": Path.home().as_posix(),
        "toolDir": HERE.as_posix(),
        "isWindows": IS_WINDOWS,
        "groupName": GROUP_NAME if GROUP_ROOT else "",
        "sessions": sessions,
    }
    # 防止会话文本里的 </script> 提前结束脚本块
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    OUTPUT.write_text(html, encoding="utf-8")
    projects = {s["project"] for s in sessions}
    running = sum(1 for s in sessions if s["live"])
    print(f"已生成 {OUTPUT}：{len(projects)} 个项目，{len(sessions)} 个会话，{running} 个正在运行")


if __name__ == "__main__":
    main()
