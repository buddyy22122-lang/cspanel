#!/bin/bash
# 由 make-launcher skill 生成：双击「Claude 会话面板.app」时运行。
# 服务器没开就在后台开起来，然后用 Chrome/Edge 的独立窗口（无地址栏、无标签页）打开。
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

URL=''             # 服务器地址；纯静态文件时留空，改填 FILE
FILE='dashboard.html'           # 纯静态文件相对本脚本的路径，如 dashboard.html；有服务器时留空
START_CMD='' # 在本脚本所在目录执行的启动命令；纯静态文件时留空
CHECK_URL='' # 用来判断服务器是否已启动的地址，必须返回 200；留空则用 URL
LOG="/tmp/claude-panel-server.log"

# 先重新扫描聊天记录，让面板是最新数据；失败也照样打开上次生成的面板
python3 build.py >/tmp/claude-panel-build.log 2>&1

if [ -n "$FILE" ]; then
  URL="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_uri())' "$FILE")"
fi
CHECK_URL="${CHECK_URL:-$URL}"

if [ -n "$START_CMD" ] && ! curl -sf -o /dev/null "$CHECK_URL"; then
  nohup bash -c "$START_CMD" >"$LOG" 2>&1 &
  for _ in $(seq 120); do curl -sf -o /dev/null "$CHECK_URL" && break; sleep 0.25; done
fi

for browser in "Google Chrome" "Microsoft Edge"; do
  if [ -d "/Applications/$browser.app" ]; then
    open -na "$browser" --args --app="$URL"
    exit 0
  fi
done
open "$URL"
