# Windows 构建说明

在 Windows 10/11 x64 上一键生成可执行程序、免安装 zip 与安装包。

## 输出产物

| 文件 | 说明 |
|------|------|
| `dist\ScreenCapture\ScreenCapture.exe` | 可直接运行的程序目录 |
| `installer\output\ScreenCapture-Portable.zip` | 免安装版，解压即用 |
| `installer\output\ScreenCaptureSetup.exe` | 安装程序 |

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

1. 安装 [ffmpeg](https://ffmpeg.org/) 并加入 PATH
2. 在「声音控制面板 → 录制」中启用「立体声混音」
