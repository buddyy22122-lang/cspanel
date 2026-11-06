# Claude 会话面板

把本机 [Claude Code](https://claude.com/claude-code) 的会话记录整理成一张可浏览、可搜索的网页：按项目分组，看提问数、工作时长、token、费用，点开能读完整对话。

- **只读**：不修改、不上传任何会话文件，也不联网，不加载任何外部字体或脚本。
- **纯静态**：生成一个 `dashboard.html`，用浏览器直接打开，不需要服务器。
- 界面是中文。

## 支持的系统

macOS 和 Windows。Linux 没测过。

## 使用

需要：Python 3、用过 Claude Code（`~/.claude` 里有会话记录）。Windows 上请安装 [python.org](https://www.python.org/downloads/) 的 Python（勾选 Add to PATH），不要用商店里的占位 `python`。

```bash
python3 build.py        # 扫描会话，生成 dashboard.html（Windows 用 python build.py）
open dashboard.html     # 用浏览器打开（Windows 用 start dashboard.html）
```

### 双击启动（可选）

**macOS：** `Claude 会话面板.app` 会先刷新数据，再用 Chrome 或 Edge 的独立窗口打开面板。第一次打开，macOS 可能提示「无法验证开发者」，因为它没有苹果的开发者认证。处理方式：在访达里**右键点它 → 打开 → 再点打开**。需要装有 Chrome 或 Edge。

**Windows：** 双击 `start.bat`，作用相同（优先用 Chrome，其次 Edge 的独立窗口）。生成日志在 `%TEMP%\claude-panel-build.log`。

### 删除会话（可选）

面板本身不能删除任何东西。想清理会话，在终端运行：

```bash
python3 delete_sessions.py <会话编号>     # Windows 用 python
```

会列出要删的会话，**输入 y 确认后才会执行**，并且只是移到废纸篓（Windows 是回收站），不会直接抹掉；正在运行的会话会被拒绝。

## 配置（可选）

默认所有项目显示在同一个列表里。想把某个目录下的项目单独分成一组，或合并改过名的文件夹，把 `config.example.json` 复制成 `config.json`（已在 `.gitignore` 中，不会提交）再修改：

| 字段 | 作用 |
| --- | --- |
| `groupRoot` | 单独成组的目录，路径在它下面的项目归入该组；支持 `~`。不写就没有分组 |
| `groupName` | 分组的显示名；不写就用目录名 |
| `renamed` | 文件夹改名后，旧会话记录里的路径还是旧名字；写「旧路径 → 新路径」就合并成一个项目 |

## 隐私

`dashboard.html` 里包含你的完整聊天内容，已写进 `.gitignore`，**不要提交或分享它**。

## 已知限制

- macOS 版本是作者原有环境；Windows 版本在 Windows 11 + Python 3.12 上测过。
- 「正在运行」检测：macOS 用 `os.kill(pid, 0)`；Windows 用 `OpenProcess`，并比对会话登记里的进程创建时间，避免 PID 被复用而误判。

## 文件

| 文件 | 作用 |
| --- | --- |
| `build.py` | 扫描会话，把数据放进模板，生成 `dashboard.html` |
| `template.html` | 面板页面（样式、界面、交互都在这里） |
| `config.example.json` | 分组和文件夹改名的配置样例（复制成 `config.json` 使用） |
| `delete_sessions.py` | 终端里删除会话（移到废纸篓） |
| `start.sh` | macOS 双击启动器调用的脚本 |
| `Claude 会话面板.app` | macOS 双击启动器 |
| `start.bat` | Windows 双击启动器 |
| `assets/icon.svg` | 图标 |
