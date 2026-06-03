# Windows 安装包构建说明

最终交付物：

| 文件 | 说明 |
|------|------|
| `installer/output/PdfToWordSetup.exe` | **安装程序**（分发给用户） |
| `dist/PdfToWord/PdfToWord.exe` | 安装后的主程序（也可直接运行测试） |

用户安装 **PdfToWordSetup.exe** 后：

1. 自动检测 Windows 版本、磁盘空间、VC++ 运行库  
2. 若缺少 VC++，自动从微软官方下载并静默安装  
3. 将程序安装到 `C:\Program Files\PdfToWord\`  
4. 创建开始菜单快捷方式（可选桌面快捷方式）  
5. 双击 **PDF 转 Word** 打开图形界面，**无需再安装 Python**

> 说明：Python 与 pdf2docx 等库已在构建时打入 `PdfToWord.exe`，终端用户电脑不需要 Python。

---

## 一、在 Windows 电脑上构建（推荐）

### 1. 准备工具

1. **Python 3.9+**  
   https://www.python.org/downloads/  
   安装时勾选 **Add python.exe to PATH**

2. **Inno Setup 6**（用于生成安装程序）  
   https://jrsoftware.org/isdl.php  
   或命令行：`winget install JRSoftware.InnoSetup`

### 2. 一键构建

以管理员或普通用户打开 **PowerShell**，进入项目目录：

```powershell
cd path\to\pdf-to-word
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
```

脚本会自动：

- 检测 / 尝试用 winget 安装 Python（构建机缺失时）
- 创建 `.venv-build` 并安装依赖
- 用 PyInstaller 打包 `PdfToWord.exe`
- 用 Inno Setup 生成 `installer\output\PdfToWordSetup.exe`

仅打包 exe、不制作安装包：

```powershell
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1 -SkipInstaller
```

### 3. 分发给用户

将 `installer\output\PdfToWordSetup.exe` 复制到 U 盘或发给用户双击安装即可。

---

## 二、在 macOS 上生成 Windows 安装包（推荐：GitHub Actions）

**Mac 无法本地运行 PyInstaller / Inno Setup 生成 `.exe`**，请在云端 Windows 环境构建。

### 步骤（网页）

1. 将项目推送到 GitHub 仓库（需包含 `pdf-to-word/` 与 `.github/workflows/pdf-to-word-windows.yml`）。
2. 打开仓库 → **Actions** → 选择 **「PDF to Word - Windows Installer」**。
3. 点击 **Run workflow** → **Run workflow**（手动触发）。
4. 等待约 5–15 分钟，进入该次运行 → 底部 **Artifacts** → 下载 **PdfToWord-Windows**。
5. 解压后得到 **`PdfToWordSetup.exe`**（安装包）和 **`PdfToWord.exe`**（程序目录）。

推送 `pdf-to-word/**` 到 `main` / `master` 时也会自动触发构建。

### 步骤（终端，已安装 [GitHub CLI](https://cli.github.com/)）

```bash
cd /path/to/zou   # 你的仓库根目录
git add pdf-to-word .github/workflows/pdf-to-word-windows.yml
git commit -m "Add PDF to Word Windows build"
git push

gh workflow run "PDF to Word - Windows Installer"
gh run watch    # 等待完成
gh run download --name PdfToWord-Windows
```

解压 `PdfToWord-Windows.zip` 即可拿到安装包。

### 其他方式（不用 GitHub）

| 方式 | 说明 |
|------|------|
| **Windows 虚拟机** | Parallels / UTM 装 Windows，在虚拟机里执行 `build.ps1` |
| **远程 Windows 电脑** | 拷贝项目到 Windows，运行 `build\windows\build.ps1` |

### macOS 本机能做什么？

在 Mac 上可直接使用图形界面（**不是** Windows 安装包）：

```bash
cd pdf-to-word
source .venv/bin/activate
pip install -r requirements.txt
python pdf_to_word_gui.py
```

---

## 三、安装程序行为说明

| 步骤 | 行为 |
|------|------|
| 环境检测 | Windows 10+、64 位、磁盘空间 |
| 运行库 | 自动检测并安装 VC++ 2015-2022 x64 |
| 安装文件 | 复制 `dist/PdfToWord/` 全部文件到安装目录 |
| 快捷方式 | 开始菜单；可选桌面图标 |
| 卸载 | 控制面板 / 设置 → 应用 → 卸载 |

---

## 四、常见问题

**Q: 必须在 Windows 上构建吗？**  
A: 是。PyInstaller 无法在当前 macOS 环境直接生成 Windows 的 `.exe`，请在 Windows 或 GitHub Actions 上构建。

**Q: 用户电脑还要装 Python 吗？**  
A: 不需要。安装包内已包含运行所需文件。

**Q: 杀毒软件报毒？**  
A: PyInstaller 打包的程序偶发误报，可对 `PdfToWord.exe` 添加信任或使用代码签名证书签名后再分发。

**Q: 安装后双击无反应？**  
A: 多为 VC++ 运行库问题。可手动安装：  
https://aka.ms/vs/17/release/vc_redist.x64.exe
