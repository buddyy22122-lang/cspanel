#!/bin/bash
# 双击运行：重新扫描 Claude 聊天记录，生成并打开面板
cd "$(dirname "$0")" || exit 1
if python3 build.py; then
  open dashboard.html
  echo "面板已在浏览器中打开，这个窗口可以关掉了。"
else
  echo "生成失败，请把上面的报错发给 Claude。"
  read -r -p "按回车关闭…"
fi
