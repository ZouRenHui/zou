; Inno Setup 安装脚本 — 生成 ImageToolSetup.exe
; 需先在 Windows 上执行 build\windows\build.ps1 生成 dist\ImageTool\

#define MyAppName "图片处理工具"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ImageTool"
#define MyAppExeName "ImageTool.exe"

[Setup]
AppId={{B7E4A1C2-3D5F-4E8B-9A1C-020000000002}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ImageTool
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=ImageToolSetup
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
Source: "scripts\install-prerequisites.ps1"; DestDir: "{tmp}\setup-scripts"; Flags: deleteafterinstall
Source: "scripts\check-environment.ps1"; DestDir: "{tmp}\setup-scripts"; Flags: deleteafterinstall
Source: "..\dist\ImageTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File ""{tmp}\setup-scripts\install-prerequisites.ps1"""; StatusMsg: "正在检测系统环境并安装所需运行库..."; Flags: runhidden waituntilterminated
