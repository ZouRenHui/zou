# PDF 工具箱

基于 Python 的 PDF 桌面工具，支持：

- **PDF 转 Word** — 将 PDF 转为 `.docx`
- **拼接 PDF** — 多个 PDF 按顺序合并，可自定义保存文件名
- **拆分 PDF** — 按单页或页码范围（如 `1-3, 5, 7-10`）拆分

图形界面采用多 Tab 设计，同时提供命令行入口。

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

| Tab | 功能 |
|-----|------|
| PDF 转 Word | 批量转换，支持同目录或指定输出目录 |
| 拼接 PDF | 多文件按列表顺序合并，可重命名保存 |
| 拆分 PDF | 每页单独拆分，或按页码范围拆分 |

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
