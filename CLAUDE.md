# 会话管理：Claude 会话面板

笔记（目标、范围、使用说明）在 `Meddes/仓库/会话管理/`。

## 日常启动
- 双击 `Claude 会话面板.app`：运行 `start.sh`，先 `python3 build.py` 重新生成 `dashboard.html`，再用 Chrome 独立窗口打开（file://，不需要服务器，不占端口）
- Windows：双击 `start.bat`，同样先生成再用 Chrome/Edge 独立窗口打开；日志在 `%TEMP%\claude-panel-build.log`
- 生成日志：`/tmp/claude-panel-build.log`；生成失败时照样打开上次的面板
- 图标：`assets/icon.svg`（和面板 favicon 同一个图案）；改图标后重新运行
  `bash ~/.claude/skills/make-launcher/scripts/make-app.sh start.sh "Claude 会话面板.app" assets/icon.svg`

## 注意
- `dashboard.html` 含完整聊天内容，已在 .gitignore 中，不要提交或上传
- 面板本身只读；删除只通过 `delete_sessions.py`（移到废纸篓/回收站，需输入 y）
- 跨平台：`build.py` 把所有路径统一成正斜杠再交给 `template.html`；进程存活检测在 `process_alive()`，Windows 上禁止用 `os.kill(pid, 0)`（会发控制台信号）
