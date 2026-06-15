# Windows 构建说明

在 Windows 10/11 x64 上一键生成可执行程序、免安装 zip 与安装包。

## 输出产物

| 文件 | 说明 |
|------|------|
| `dist\ScreenCapture\ScreenCapture.exe` | 可直接运行的程序目录 |
| `installer\output\ScreenCapture-Portable.zip` | 免安装版，解压即用 |
| `installer\output\ScreenCaptureSetup.exe` | 安装程序 |
| `installer\output\ScreenCaptureUninstall.exe` | **卸载旧版本**（安装新版前运行） |

## 升级安装（推荐流程）

1. 运行 **ScreenCaptureUninstall.exe** 卸载旧版本
2. 运行 **ScreenCaptureSetup.exe** 安装新版本

若已安装过旧版，也可在开始菜单使用「卸载 录屏截屏工具」。独立卸载程序适合安装记录异常或需彻底清理时使用。

开发/源码目录下也可双击 `installer\卸载录屏截屏工具.bat` 调用 PowerShell 卸载脚本。

## 本地构建

```powershell
cd screen-capture-tool
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
```

仅打包 exe 和免安装 zip（跳过安装包）：

```powershell
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1 -SkipInstaller
```

## 依赖

- Python 3.9+
- Inno Setup 6（生成安装包）：`winget install JRSoftware.InnoSetup`

## CI 自动构建

推送到 `main`/`master` 且修改 `screen-capture-tool/**` 时，GitHub Actions 会自动构建并上传 Artifact。

在 Actions 页面下载 **ScreenCapture-Windows** 即可获取：

- `ScreenCapture-Portable.zip` — 解压后双击 `ScreenCapture.exe`
- `ScreenCaptureSetup.exe` — 安装到系统

## 录制系统声音（Windows）

1. 安装 [ffmpeg](https://ffmpeg.org/) 并加入 PATH（安装后需**重启录屏工具**）
2. 程序会依次尝试 **WASAPI 环回** 与 **立体声混音** 采集系统声音
3. 若带音频的 ffmpeg 启动失败，会自动回退为**仅画面**录制（内置 mss 或 ffmpeg 无音频模式）
4. 立体声混音：控制面板 → 声音 → 录制 → 启用「立体声混音」

> 安装 ffmpeg 后若录屏异常，多为音频设备不可用导致 ffmpeg 秒退；新版本已自动回退，无需手动卸载 ffmpeg。
