# 语音工具箱

Python 图形界面工具，支持语音转文字与文字转语音。

## 功能

### 语音转文字

- 上传音频（mp3、wav、m4a 等）或视频（mp4、mov、mkv 等）
- 使用 Whisper 模型离线识别语音
- 在预览区显示识别结果
- 保存为 TXT 或 Word（.docx）

### 文字转语音

- 上传 Word、TXT、PDF、PPT 等文档，提取正文
- 使用 Microsoft Edge 在线语音服务合成 MP3
- 支持多种中文 / 英文发音人与语速调节
- 可播放生成的音频文件

## 环境要求

- Python 3.10+
- **视频文件**：需安装 [ffmpeg](https://ffmpeg.org/)
  - macOS：`brew install ffmpeg`
  - Windows：从官网下载并加入 PATH
- **文字转语音**：需要联网（edge-tts）
- **首次语音识别**：会自动下载 Whisper 模型（体积因模型而异）

## 安装与运行

### 从源码运行（macOS / Linux / Windows）

```bash
cd speech-toolbox
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python speech_toolbox_gui.py
```

### Windows 安装包 / 免安装版

| 文件 | 说明 |
|------|------|
| `SpeechToolboxSetup.exe` | 安装程序，写入系统并创建快捷方式 |
| `SpeechToolbox-Portable.zip` | 免安装版，解压即用 |

获取方式：

1. 推送到 GitHub 后，在 **Actions** 页下载 **SpeechToolbox-Windows** Artifact
2. 或在 Windows 上本地构建，见 [BUILD-WINDOWS.md](BUILD-WINDOWS.md)

## 使用说明

### 语音转文字

1. 切换到「语音转文字」标签
2. 选择音频或视频文件
3. 可选：调整识别模型与语言
4. 点击「开始识别」
5. 在预览区查看结果，可保存为 TXT 或 Word

模型越大识别越准，但速度更慢、占用更多内存。一般推荐 `base` 或 `small`。

### 文字转语音

1. 切换到「文字转语音」标签
2. 选择文档文件
3. 点击「提取文字」查看正文（也可在预览区直接编辑）
4. 选择发音人、语速与输出路径
5. 点击「生成语音」
6. 完成后可点击「播放音频」试听

## 支持格式

| 类型 | 格式 |
|------|------|
| 音频 | wav, mp3, m4a, aac, flac, ogg, wma |
| 视频 | mp4, mov, avi, mkv, webm, wmv, flv, m4v |
| 文档 | txt, md, docx, pdf, pptx, doc, rtf（ppt 需先转 pptx） |
