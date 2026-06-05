# Windows 安装包构建说明

最终交付物：

| 文件 | 说明 |
|------|------|
| `installer/output/ImageToolSetup.exe` | **安装程序**（分发给用户） |
| `dist/ImageTool/ImageTool.exe` | 安装后的主程序（也可直接运行测试） |

用户安装 **ImageToolSetup.exe** 后：

1. 自动检测 Windows 版本、磁盘空间、VC++ 运行库、Tesseract  
2. 若缺少 VC++ / Tesseract，自动下载并静默安装  
3. 将程序安装到 `C:\Program Files\ImageTool\`  
4. 创建开始菜单快捷方式（可选桌面快捷方式）  
5. 双击 **图片处理工具** 打开图形界面，**无需再安装 Python**

> 说明：Python 与 Pillow、PaddleOCR 等库已在构建时打入 `ImageTool.exe`。首次 OCR 仍需联网下载 Paddle 模型（写入用户目录）。

---

## 一、在 Windows 电脑上构建

### 1. 准备工具

1. **Python 3.9+** — https://www.python.org/downloads/（勾选 Add to PATH）  
2. **Inno Setup 6** — https://jrsoftware.org/isdl.php 或 `winget install JRSoftware.InnoSetup`

### 2. 一键构建

```powershell
cd path\to\image-tool
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
```

仅打包 exe、不制作安装包：

```powershell
powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1 -SkipInstaller
```

---

## 二、在 macOS 上生成 Windows 安装包（GitHub Actions）

Mac 无法本地生成 Windows `.exe`，请使用 GitHub Actions。

### 步骤（网页）

1. 将仓库推送到 GitHub（需包含 `image-tool/` 与 `.github/workflows/image-tool-windows.yml`）。
2. 打开仓库 → **Actions** → **Image Tool - Windows Installer**。
3. 点击 **Run workflow** → **Run workflow**。
4. 等待约 **20–40 分钟**（含 PaddleOCR 打包）。
5. 进入该次运行 → **Artifacts** → 下载 **ImageTool-Windows**。
6. 解压得到 **`ImageToolSetup.exe`**。

推送 `image-tool/**` 到 `main` / `master` 时也会自动触发。

### 步骤（GitHub CLI）

```bash
cd /path/to/zou
git add image-tool .github/workflows/image-tool-windows.yml
git commit -m "Add Image Tool Windows build"
git push

gh workflow run "Image Tool - Windows Installer"
gh run watch
gh run download --name ImageTool-Windows
```

---

## 三、安装程序行为

| 步骤 | 行为 |
|------|------|
| 环境检测 | Windows 10+、64 位、磁盘空间 |
| VC++ 运行库 | 自动检测并安装 |
| Tesseract OCR | 未安装时自动安装（Tesseract 引擎需要） |
| 安装文件 | 复制 `dist/ImageTool/` 到安装目录 |
| 快捷方式 | 开始菜单；可选桌面图标 |

---

## 四、常见问题

**Q: GitHub Actions 构建失败？**  
A: 查看 **Build exe and installer** 日志。常见原因：PaddlePaddle 安装失败（网络）、PyInstaller 超时（已设 180 分钟）。

**Q: 用户还要装 Python 吗？**  
A: 不需要。

**Q: OCR 首次很慢？**  
A: 首次需下载 Paddle 模型（数百 MB），属正常现象。

**Q: 安装后双击无反应？**  
A: 手动安装 VC++：https://aka.ms/vs/17/release/vc_redist.x64.exe
