; Inno Setup 安装脚本 — 生成 ScreenCaptureSetup.exe
; 需先在 Windows 上执行 build\windows\build.ps1 生成 dist\ScreenCapture\

#define MyAppName "录屏截屏工具"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ScreenCapture"
#define MyAppExeName "ScreenCapture.exe"

[Setup]
AppId={{C3D8E2F1-4A6B-5C9D-0E1F-030000000003}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ScreenCapture
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=ScreenCaptureSetup
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
Source: "..\dist\ScreenCapture\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File ""{tmp}\setup-scripts\install-prerequisites.ps1"""; StatusMsg: "正在检测系统环境并安装所需运行库..."; Flags: runhidden waituntilterminated
