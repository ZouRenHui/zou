; Inno Setup 安装脚本 — 生成 PdfToWordSetup.exe
; 需先在 Windows 上执行 build\windows\build.ps1 生成 dist\PdfToWord\

#define MyAppName "PDF 工具箱"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "PdfToWord"
#define MyAppExeName "PdfToWord.exe"

[Setup]
AppId={{A8F3C2E1-9B4D-4F6A-8C2E-010000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PdfToWord
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=PdfToWordSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加选项:"; Flags: unchecked

[Files]
; 环境检测脚本（安装前解压到临时目录）
Source: "scripts\install-prerequisites.ps1"; DestDir: "{tmp}\setup-scripts"; Flags: deleteafterinstall
Source: "scripts\check-environment.ps1"; DestDir: "{tmp}\setup-scripts"; Flags: deleteafterinstall
; 主程序（由 PyInstaller 生成）
Source: "..\dist\PdfToWord\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后：检测环境并自动安装 VC++ 等运行库
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File ""{tmp}\setup-scripts\install-prerequisites.ps1"""; StatusMsg: "正在检测系统环境并安装所需运行库..."; Flags: runhidden waituntilterminated
