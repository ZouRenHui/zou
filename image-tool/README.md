# 图片处理工具

基于 Python 与 Tkinter 的桌面图片工具，支持水印、尺寸调整、简单编辑与 OCR 文字识别。

## 环境要求

- Python 3.9+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)（仅「文字识别」功能需要）

### 安装 Tesseract

**macOS：**

```bash
brew install tesseract tesseract-lang
```

**Windows：** 从 [UB Mannheim 镜像](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装，并将安装目录加入 PATH。

## 安装

```bash
cd image-tool
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 启动图形界面

```bash
python image_tool_gui.py
```

## 功能说明

### 1. 水印

- 支持**文字水印**与 **Logo 图片水印**
- 可调整字号、颜色、透明度、位置（九宫格或平铺）
- 支持单张图片或批量处理整个文件夹
- **去除水印**：框选固定区域，使用图像修复算法去除半透明文字/Logo（适合批量同位置水印）

> 去水印说明：需准确框选水印区域；复杂全图水印或大面积水印效果有限，修复后可能有轻微痕迹。

### 2. 格式转换

- 在 JPG、PNG、WebP、BMP、GIF、TIFF 之间批量互转
- 内置压缩质量预设（原画 / 高质量 / 标准 / 网页 / 高压缩 / 极小）
- 透明 PNG 转 JPEG 时自动填充白色背景

### 3. 压缩

- 质量预设快速选择，也支持自定义数值
- 可选同时缩小尺寸（限制最大边长）
- 可统一输出为 JPEG 以获得更小体积
- 日志显示每张图片压缩前后大小与节省比例

### 4. 调整尺寸

- 限制最大边长（等比缩放）
- 指定宽度 × 高度（可选保持宽高比）
- 仅指定宽度或高度
- 支持批量处理，输出质量可选预设

### 5. 编辑

- 打开单张图片进行预览
- 旋转（90° 快捷或自定义角度）
- 水平 / 垂直翻转
- 鼠标拖拽框选裁剪区域，或手动输入坐标
- 编辑仅更新预览，**保存当前图片** 时弹出另存为对话框选择路径

### 6. 文字识别（OCR）

- **PaddleOCR（默认，高精度）**：适合中文、复杂排版、截图，支持文字方向校正
- **Tesseract（轻量备选）**：无需大模型，适合简单英文/离线场景
- 图像预处理、小图自动放大
- 结果实时显示，可导出 **TXT** / **Word (.docx)**

**安装 PaddleOCR：**

```bash
pip install paddlepaddle paddleocr
```

首次使用会自动下载模型（需联网，约 1~2 分钟）。

**提高准确率建议：**
- 默认使用 **PaddleOCR** + **自动增强** + **自动放大**
- 拍照/曲面文档：勾选「文档矫正」（较慢）
- 纯英文可切换 Tesseract 并选 `eng` 语言包

## 支持的图片格式

JPG、PNG、BMP、GIF、WebP、TIFF

## 说明

- 批量处理时默认在原文件名后追加后缀（如 `_watermarked`、`_compressed`），不会覆盖原图。
- OCR 识别效果取决于图片清晰度与 Tesseract 语言包是否已安装。

## Windows 安装包

在 Windows 上构建，或在 Mac 上通过 **GitHub Actions** 云端构建 `ImageToolSetup.exe`。

详细步骤见 **[BUILD-WINDOWS.md](BUILD-WINDOWS.md)**（与 pdf-to-word 相同流程）。

快速命令（Windows 本机）：

```powershell
cd image-tool
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
```

输出：`installer\output\ImageToolSetup.exe`
