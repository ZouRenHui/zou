# Windows 构建说明

在 Windows 10/11 x64 上一键生成可执行程序、免安装 zip 与安装包。

## 输出产物

| 文件 | 说明 |
|------|------|
| `dist\SpeechToolbox\SpeechToolbox.exe` | 可直接运行的程序目录 |
| `installer\output\SpeechToolbox-Portable.zip` | 免安装版，解压即用 |
| `installer\output\SpeechToolboxSetup.exe` | 安装程序 |

## 本地构建

```powershell
cd speech-toolbox
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

推送到 `main`/`master` 且修改 `speech-toolbox/**` 时，GitHub Actions 会自动构建并上传 Artifact。

在 Actions 页面下载 **SpeechToolbox-Windows** 即可获取：

- `SpeechToolbox-Portable.zip` — 解压后双击 `SpeechToolbox.exe`
- `SpeechToolboxSetup.exe` — 安装到系统

## 用户使用说明

- **语音识别**首次运行会自动下载 Whisper 模型，需联网
- **文字转语音**需要联网（edge-tts）
- **视频文件**处理需用户自行安装 [ffmpeg](https://ffmpeg.org/) 并加入 PATH
