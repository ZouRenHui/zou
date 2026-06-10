# 录屏 / 截屏工具

Python 图形界面工具，支持屏幕录制与截图。

## 功能

- **录屏**：开始 / 结束录制，结束后弹出保存对话框
- **系统声音**：通过 ffmpeg 采集（macOS 需配合 BlackHole 等虚拟声卡路由系统输出）
- **全屏截屏**：一键捕获整个虚拟桌面
- **区域截屏**：鼠标拖拽选择区域
- **剪贴板**：截屏后自动复制，可直接粘贴到 Word、微信、记事本等
- **保存图片**：可选 PNG / JPEG

## 环境要求

- Python 3.10+
- **录屏含音频**：需安装 [ffmpeg](https://ffmpeg.org/)
  - macOS：`brew install ffmpeg`
  - Windows：从官网下载并加入 PATH
- **macOS 系统声音**：安装 [BlackHole](https://existential.audio/blackhole/)，在「音频 MIDI 设置」中创建多输出设备（扬声器 + BlackHole），并将系统输出设为该设备

未安装 ffmpeg 时，录屏仍可用（仅画面，使用 mss + OpenCV）。

## Windows 发布包

GitHub Actions 会在推送后自动构建 Windows 版本，在仓库 **Actions** 页下载 **ScreenCapture-Windows** Artifact：

- **ScreenCapture-Portable.zip** — 解压即用，双击 `ScreenCapture.exe`
- **ScreenCaptureSetup.exe** — 安装版，带开始菜单快捷方式

本地构建见 [BUILD-WINDOWS.md](BUILD-WINDOWS.md)。

## 安装与运行

```bash
cd screen-capture-tool
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python screen_capture_gui.py
```

## macOS 权限（重要）

截屏和录屏都需要「屏幕录制」权限。未授权时，截图可能**只有桌面壁纸、看不到窗口内容**。

1. 运行一次截屏，若失败会提示打开设置
2. 或手动前往：**系统设置 → 隐私与安全性 → 屏幕录制**
3. 勾选你运行本工具的程序（Terminal、iTerm、Python 等）
4. **完全退出并重新启动**该程序后生效

## 使用说明

### 录屏

1. 切换到「录屏」标签
2. 点击「开始录制」
3. 再次点击「结束录制」
4. 在弹窗中选择保存路径

### 截屏

1. 切换到「截屏」标签
2. 点击「全屏截屏」或「区域截屏」
3. 截图自动进入剪贴板，可在其他应用中粘贴
4. 需要文件时点击「保存为图片」
