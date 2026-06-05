# PDF 转 Word 工具

基于 Python 与 [pdf2docx](https://github.com/dothinking/pdf2docx)，将 PDF 转为 `.docx`。支持**图形界面**与命令行。

## 环境要求

- Python 3.9+

## 安装

```bash
cd pdf-to-word
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 图形界面（推荐）

```bash
python pdf_to_word_gui.py
```

- **添加文件 / 添加文件夹**：可多选 PDF，或扫描整个文件夹
- **输出到 PDF 同目录**：默认勾选，生成的 `.docx` 与源文件放在一起
- **输出目录**：取消勾选后可指定统一输出文件夹
- **开始转换**：后台执行，进度条与日志会实时更新

## 命令行

```bash
# 单文件，输出为同目录下的 report.docx
python pdf_to_word.py report.pdf

# 指定输出路径
python pdf_to_word.py report.pdf -o ~/Desktop/report.docx

# 转换目录内所有 PDF，输出到 output/
python pdf_to_word.py ./pdfs/ -o ./output/

# 递归处理子目录
python pdf_to_word.py ./pdfs/ -o ./output/ -r
```

## 麒麟 / Linux 版本

请参阅 **[BUILD-KYLIN.md](BUILD-KYLIN.md)**：

- **`PdfToWord-Kylin-x86_64.tar.gz`** — 免安装版，解压后执行 `./run.sh`
- **`install-kylin.sh`** — 脚本安装版，自动检测并安装 Python 依赖

在 Mac 上可通过 GitHub Actions **「PDF to Word - Linux/Kylin Build」** 自动构建。

## Windows 安装包

需要分发给 Windows 用户时，请参阅 **[BUILD-WINDOWS.md](BUILD-WINDOWS.md)**：

- 在 Windows 上运行 `build\windows\build.ps1` 生成：
  - **`PdfToWord-Portable.zip`** — 免安装版，解压即用
  - **`PdfToWordSetup.exe`** — 安装程序版
- 双击 **`PdfToWord.exe`** 即可打开图形界面（无需安装 Python）
- 安装程序版会自动检测环境并安装 VC++ 运行库等依赖

## 说明

- 适合**文字版 PDF**（可选中复制文字），版式会尽量保留。
- **扫描件 / 图片型 PDF** 需先做 OCR，本工具不会自动识别图片中的文字。
- 复杂排版、特殊字体或加密 PDF 可能转换不完整，需在 Word 中手动微调。
