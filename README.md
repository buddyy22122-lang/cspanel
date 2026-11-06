# Claude 会话面板

把本机 [Claude Code](https://claude.com/claude-code) 的会话记录整理成一张可浏览、可搜索的网页：按项目分组，看提问数、工作时长、token、费用，点开能读完整对话。

- **只读**：不修改、不上传任何会话文件，也不联网，不加载任何外部字体或脚本。
- **纯静态**：生成一个 `dashboard.html`，用浏览器直接打开，不需要服务器。
- 界面是中文。

## 目前只支持 macOS

Windows / Linux 暂时不能用（见下方「已知限制」）。

## 使用

需要：macOS、Python 3、用过 Claude Code（`~/.claude` 里有会话记录）。

```bash
python3 build.py        # 扫描会话，生成 dashboard.html
open dashboard.html     # 用浏览器打开
```

### 双击启动（可选）

`Claude 会话面板.app` 会先刷新数据，再用 Chrome 或 Edge 的独立窗口打开面板。

第一次打开，macOS 可能提示「无法验证开发者」，因为它没有苹果的开发者认证。处理方式：在访达里**右键点它 → 打开 → 再点打开**。需要装有 Chrome 或 Edge。

### 删除会话（可选）

面板本身不能删除任何东西。想清理会话，在终端运行：

```bash
python3 delete_sessions.py <会话编号>
```

会列出要删的会话，**输入 y 确认后才会执行**，并且只是移到废纸篓，不会直接抹掉；正在运行的会话会被拒绝。

## 隐私

`dashboard.html` 里包含你的完整聊天内容，已写进 `.gitignore`，**不要提交或分享它**。

## 已知限制

- 只在 macOS 上测试过。
- 「正在运行」检测用 `os.kill(pid, 0)`，在 Windows 上含义不同，可能干扰进程，请不要在 Windows 上运行。
- `delete_sessions.py` 通过访达移到废纸篓，仅限 macOS。
- 面板会把 `~/Documents/Meddes` 下的项目单独分成一组，其他人没有这个文件夹，会全部归到「其他项目」。
- `build.py` 里的 `RENAMED` 是作者自己的文件夹改名记录，可按需清空或改成自己的。

## 文件

| 文件 | 作用 |
| --- | --- |
| `build.py` | 扫描会话，把数据放进模板，生成 `dashboard.html` |
| `template.html` | 面板页面（样式、界面、交互都在这里） |
| `delete_sessions.py` | 终端里删除会话（移到废纸篓） |
| `start.sh` | 双击启动器调用的脚本 |
| `Claude 会话面板.app` | 双击启动器 |
| `assets/icon.svg` | 图标 |
