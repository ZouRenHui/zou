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

### 方式 A：一键安装（推荐，只需 1 个文件）

1. 从 **Releases** 或 **Artifacts** 下载 **`PdfToWord-Kylin-aarch64.run`**
2. 右键 → 属性 → 权限 → 勾选 **「允许作为程序执行」**
3. **双击** `PdfToWord-Kylin-aarch64.run`
4. 等待安装完成（首次需联网安装 Python 依赖，约 1–3 分钟）
5. 自动创建桌面快捷方式并启动 **「PDF 工具箱」**

> 新版在麒麟上会自动使用 **Python 模式** 安装，避免 libexpat.so 安全拦截。  
> 也可双击 **`一键安装-PDF工具箱.desktop`**（与 .run 放在同一文件夹）。

终端等价命令：

```bash
chmod +x PdfToWord-Kylin-aarch64.run
./PdfToWord-Kylin-aarch64.run
```

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

### 麒麟安全认证：libexpat.so 未认证应用

**现象：** 双击桌面快捷方式时，弹出「发现未认证应用执行」，涉及 `libexpat.so.1` 等文件。

**原因：** PyInstaller 打包程序自带 `_internal/libexpat.so.1`，麒麟安全机制会拦截。

**解决办法（推荐）：改用 Python 模式**

在已安装的 `PdfToWord` 目录执行（新版安装包已自带 `app_source`）：

```bash
cd ~/.local/share/PdfToWord
chmod +x install-kylin-python.sh
./install-kylin-python.sh
```

脚本会：
1. 用系统 Python 安装到 `~/.local/share/pdf-to-word/`
2. 重建桌面快捷方式（不再启动 PyInstaller 二进制）
3. 避免 libexpat.so 安全拦截

之后从桌面双击 **「PDF 工具箱」** 即可。

**临时办法：** 在安全认证框中选择 **允许 / 信任**（每次或永久，视系统策略而定）。

**备选：** 将整个 `pdf-to-word` 源码拷到麒麟，运行 `installer/linux/install-kylin.sh`。

---

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
