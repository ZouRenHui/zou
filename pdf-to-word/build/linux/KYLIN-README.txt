PDF 工具箱 — 麒麟 / Linux 免安装版
====================================

功能：PDF 转 Word、拼接 PDF、拆分 PDF

【使用方法】
1. 解压本压缩包到任意目录，例如：
   ~/PdfToWord  或  /opt/PdfToWord  或  U 盘目录
2. 进入 PdfToWord 文件夹
3. 双击运行 run.sh，或在终端执行：
   chmod +x run.sh PdfToWord
   ./run.sh

【注意事项】
- 请勿单独移动 PdfToWord 可执行文件，需与同目录下所有文件放在一起
- 若提示权限不足，请执行：chmod +x run.sh PdfToWord
- 若无法启动图形界面，请确认系统已安装图形环境与 Tk 支持
- 删除整个 PdfToWord 文件夹即可卸载

【适用系统】
- 银河麒麟桌面版 V10 / V10 SP1（x86_64）
- openKylin
- 其他基于 Debian / Ubuntu 的国产 Linux 桌面系统

【常见问题】
- 缺少 libGL：sudo apt install libgl1   （或联系管理员安装对应运行库）
- 双击无反应：请在终端运行 ./run.sh 查看错误信息
