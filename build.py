#!/usr/bin/env python3
"""扫描 ~/.claude/projects 下的会话文件，生成 dashboard.html。

只读：不修改、不删除任何会话文件，也不联网。
用法：python3 build.py  然后打开 dashboard.html
"""
import glob
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
MEDDES_ROOT = str(Path.home() / "Documents" / "Meddes")
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
OUTPUT = HERE / "dashboard.html"


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone()
    except (AttributeError, ValueError):
        return None


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


def read_session(path):
    session = {
        "id": Path(path).stem,
        "cwd": None,
        "customTitle": None,
        "aiTitle": None,
        "firstPrompt": None,
        "prompts": 0,
        "replies": 0,
        "models": Counter(),
        "start": None,
        "end": None,
        "promptDays": Counter(),
        "entrypoint": None,
    }
    reply_ids = set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("type")
            session["cwd"] = session["cwd"] or rec.get("cwd")
            session["entrypoint"] = session["entrypoint"] or rec.get("entrypoint")
            if t == "custom-title" and rec.get("customTitle"):
                session["customTitle"] = rec["customTitle"]
            elif t == "ai-title" and rec.get("aiTitle"):
                session["aiTitle"] = rec["aiTitle"]

            ts = parse_ts(rec.get("timestamp")) if rec.get("timestamp") else None
            if ts:
                session["start"] = min(session["start"] or ts, ts)
                session["end"] = max(session["end"] or ts, ts)

            text = human_prompt_text(rec)
            if text is not None:
                session["prompts"] += 1
                session["firstPrompt"] = session["firstPrompt"] or text[:80]
                if ts:
                    session["promptDays"][ts.strftime("%Y-%m-%d")] += 1
            elif t == "assistant" and not rec.get("isSidechain"):
                msg = rec.get("message") or {}
                mid = msg.get("id") or rec.get("uuid")
                if mid not in reply_ids:
                    reply_ids.add(mid)
                    session["replies"] += 1
                    model = msg.get("model")
                    if model and not model.startswith("<"):
                        session["models"][model] += 1

    if session["end"] is None:
        mtime = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).astimezone()
        session["start"] = session["end"] = mtime
    return session


def main():
    sessions = []
    for path in glob.glob(str(PROJECTS_DIR / "*" / "*.jsonl")):
        s = read_session(path)
        if not s["cwd"] or (s["prompts"] == 0 and s["replies"] == 0):
            continue
        title = s["customTitle"] or s["aiTitle"] or s["firstPrompt"] or "（无标题）"
        sessions.append({
            "id": s["id"],
            "project": s["cwd"],
            "isMeddes": s["cwd"] == MEDDES_ROOT or s["cwd"].startswith(MEDDES_ROOT + "/"),
            "title": title,
            "firstPrompt": s["firstPrompt"] or "",
            "prompts": s["prompts"],
            "replies": s["replies"],
            "model": s["models"].most_common(1)[0][0] if s["models"] else "",
            "start": s["start"].isoformat(timespec="minutes"),
            "end": s["end"].isoformat(timespec="minutes"),
            "promptDays": dict(s["promptDays"]),
            "entrypoint": s["entrypoint"] or "",
        })

    data = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="minutes"),
        "home": str(Path.home()),
        "meddesRoot": MEDDES_ROOT,
        "sessions": sessions,
    }
    # 防止会话文本里的 </script> 提前结束脚本块
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    OUTPUT.write_text(html, encoding="utf-8")
    projects = {s["project"] for s in sessions}
    print(f"已生成 {OUTPUT}：{len(projects)} 个项目，{len(sessions)} 个会话")


if __name__ == "__main__":
    main()
