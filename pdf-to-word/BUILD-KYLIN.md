# 麒麟 / Linux 版本说明（PDF 工具箱 v1.1）

提供两种方式在**银河麒麟**、**openKylin** 及其他 Linux 桌面上使用：

| 方式 | 文件 | 适合场景 |
|------|------|----------|
| **免安装版** | `PdfToWord-Kylin-x86_64.tar.gz` | 解压即用，可放 U 盘 |
| **脚本安装版** | `install-kylin.sh` | 有 Python 环境，自动装依赖 |

---

## 一、免安装版（推荐）

### 在 Mac 上通过 GitHub Actions 构建

```bash
cd /Users/zou/Documents/GitHub/zou
git push   # 推送后自动构建，或 Actions 手动 Run workflow
```

### 方式 A：GitHub Releases 直接下载（**推荐，无需解压 zip**）

1. 打开仓库 → **Releases**
2. 找到最新的 `PDF Toolbox Kylin Build`（需先在 Actions 手动 **Run workflow** 触发）
3. 直接下载 **`PdfToWord-Kylin-x86_64.run`**（不是 zip）
4. 在麒麟终端执行：

```bash
chmod +x PdfToWord-Kylin-x86_64.run
./PdfToWord-Kylin-x86_64.run
```

`.run` 是自解压脚本，会安装到 `~/.local/share/PdfToWord`，自动创建桌面快捷方式并启动程序。

### 方式 B：从 Actions Artifacts 下载

GitHub 会把文件包在 **`PdfToWord-Kylin.zip`** 里。若图形界面无法解压，用终端：

```bash
# 方法1
sudo apt install unzip
unzip PdfToWord-Kylin.zip

# 方法2（麒麟通常自带 Python）
python3 -m zipfile -e PdfToWord-Kylin.zip .

# 方法3
sudo apt install p7zip-full
7z x PdfToWord-Kylin.zip
```

解压后得到 `PdfToWord-Kylin-x86_64.run` 或 `.tar.gz`，优先使用 `.run`。

### 在麒麟本机构建

```bash
cd pdf-to-word
chmod +x build/linux/build.sh installer/linux/install-kylin.sh
./build/linux/build.sh
```

产物：`installer/output/PdfToWord-Kylin-$(uname -m).tar.gz`

### 用户使用

```bash
# 推荐：自解压 .run（一条命令）
chmod +x PdfToWord-Kylin-x86_64.run
./PdfToWord-Kylin-x86_64.run

# 备选：tar.gz
tar -xzf PdfToWord-Kylin-x86_64.tar.gz
cd PdfToWord
chmod +x run.sh PdfToWord check-kylin.sh
./run.sh
```

**注意：** Linux 版主程序名为 `PdfToWord`（无 `.exe`），建议用 `run.sh` 或在终端执行 `./PdfToWord`。

### 图形界面一键安装（推荐，方式二）

将以下文件放在**同一文件夹**（如「下载」）：

- `PdfToWord-Kylin-aarch64.tar.gz`（ARM 麒麟）
- `setup-kylin.sh`
- `setup-kylin.desktop`（可选，双击图标安装）

**双击 `setup-kylin.sh`**，在弹出框中选择 **「运行」** 或 **「在终端中运行」**。

脚本会自动：解压 → 安装到 `~/.local/share/PdfToWord` → 创建桌面快捷方式 → 询问是否启动。

> 若双击无反应：右键 → 属性 → 权限 → 勾选「允许作为程序执行」，或终端执行 `chmod +x setup-kylin.sh && ./setup-kylin.sh`

### 手动创建桌面快捷方式

解压得到 `PdfToWord` 文件夹后：

```bash
cd PdfToWord
chmod +x install-shortcut.sh
./install-shortcut.sh
```

---

## 二、脚本安装版

适合可以联网、允许安装系统包的环境：

```bash
cd pdf-to-word
chmod +x installer/linux/install-kylin.sh
./installer/linux/install-kylin.sh
```

脚本会：

1. 检测 `apt` / `yum` / `dnf`，安装 `python3`、`python3-tk` 等  
2. 创建虚拟环境并安装 `pdf2docx`  
3. 在应用菜单添加 **「PDF 转 Word」** 入口  
4. 命令行可用：`pdf-to-word`

---

## 三、系统兼容性（重要）

**报错「无法执行二进制文件：可执行文件格式错误」= CPU 架构下错了包。**

先在麒麟终端执行：

```bash
uname -m
```

| `uname -m` 结果 | 应下载的文件 |
|-----------------|--------------|
| `x86_64` | `PdfToWord-Kylin-x86_64.run` |
| `aarch64` | `PdfToWord-Kylin-aarch64.run`（飞腾、鲲鹏等 ARM 电脑） |

验证程序包架构：

```bash
file PdfToWord
# x86 电脑应显示 x86-64；ARM 电脑应显示 aarch64
```

### ARM 电脑无法用预编译包时（源码安装）

```bash
# 将完整 pdf-to-word 项目文件夹拷到麒麟
chmod +x installer/linux/install-kylin.sh
./installer/linux/install-kylin.sh
# 然后从应用菜单打开「PDF 工具箱」，或执行 pdf-to-word
```

> GitHub Actions 默认构建 **x86_64**。ARM 版麒麟请在 ARM 机器上执行 `build.sh`。

---

## 四、常见问题

**Q: 双击无反应？**  
在终端运行 `./run.sh` 查看报错。

**Q: 提示缺少 libGL？**

```bash
sudo apt install libgl1
# 或
sudo dnf install mesa-libGL
```

**Q: 中文界面乱码？**  
确认系统已安装中文字体（麒麟桌面通常已自带）。

**Q: 与 Windows 版区别？**  
功能相同；Linux 免安装包为 `.tar.gz`，启动文件为 `PdfToWord`（无 `.exe`）。
