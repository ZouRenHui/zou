# 麒麟 / Linux 版本说明

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

打开 **Actions → PDF to Word - Linux/Kylin Build**，完成后在 **Artifacts** 下载：

- **`PdfToWord-Kylin-x86_64.tar.gz`**

### 在麒麟本机构建

```bash
cd pdf-to-word
chmod +x build/linux/build.sh installer/linux/install-kylin.sh
./build/linux/build.sh
```

产物：`installer/output/PdfToWord-Kylin-$(uname -m).tar.gz`

### 用户使用

```bash
tar -xzf PdfToWord-Kylin-x86_64.tar.gz
cd PdfToWord
chmod +x run.sh PdfToWord
./run.sh
```

或在文件管理器中进入 `PdfToWord` 文件夹，双击 `run.sh`。

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

## 三、系统兼容性

| 系统 | 架构 | 说明 |
|------|------|------|
| 银河麒麟 V10 / V10 SP1 | x86_64 | CI 构建包可直接尝试 |
| openKylin | x86_64 | 同上 |
| 鲲鹏 / 飞腾等 | aarch64 | 需在对应机器上运行 `build/linux/build.sh` 本地构建 |

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
