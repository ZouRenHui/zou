; Inno Setup — 独立卸载程序 ScreenCaptureUninstall.exe
; 编译：build\windows\build.ps1 或 iscc installer\uninstall.iss

#define TargetAppId "{C3D8E2F1-4A6B-5C9D-0E1F-030000000003}"
#define TargetAppName "录屏截屏工具"
#define TargetExeName "ScreenCapture.exe"
#define TargetFolder "ScreenCapture"

[Setup]
AppId={{E5F0A3B2-6C7D-4E1F-2A3B-050000000005}
AppName={#TargetAppName} 卸载程序
AppVersion=1.0.0
AppPublisher=ScreenCapture
DefaultDirName={tmp}\ScreenCaptureUninstall
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=no
DisableFinishedPage=no
OutputDir=output
OutputBaseFilename=ScreenCaptureUninstall
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
Uninstallable=no
CloseApplications=yes
CloseApplicationsFilter=*.exe,ScreenCapture.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppTitle={#TargetAppName} Uninstall
SetupWindowTitle={#TargetAppName} Uninstall
ButtonInstall=Uninstall
ButtonNext=Uninstall

[Code]
const
  TargetAppId = '{#TargetAppId}';
  TargetAppName = '{#TargetAppName}';
  TargetExeName = '{#TargetExeName}';

function KillRunningApp(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if Exec('taskkill.exe', '/F /IM ' + TargetExeName, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Sleep(1000);
end;

function RegUninstallKey(): String;
begin
  Result := 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\' + TargetAppId + '_is1';
end;

function FindUninstallString(var UninstallCmd: String): Boolean;
begin
  Result := False;
  UninstallCmd := '';
  if RegQueryStringValue(HKLM64, RegUninstallKey(), 'UninstallString', UninstallCmd) then
    Result := True
  else if RegQueryStringValue(HKLM32, RegUninstallKey(), 'UninstallString', UninstallCmd) then
    Result := True;
end;

function FindInstallLocation(var InstallLocation: String): Boolean;
begin
  Result := False;
  InstallLocation := '';
  if RegQueryStringValue(HKLM64, RegUninstallKey(), 'InstallLocation', InstallLocation) then
    Result := True
  else if RegQueryStringValue(HKLM32, RegUninstallKey(), 'InstallLocation', InstallLocation) then
    Result := True;
end;

function RemoveDirRecursive(const DirName: String): Boolean;
var
  FindRec: TFindRec;
  FilePath: String;
begin
  Result := True;
  if not DirExists(DirName) then
    Exit;

  if FindFirst(DirName + '\*', FindRec) then
  try
    repeat
      if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
      begin
        FilePath := DirName + '\' + FindRec.Name;
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          if not RemoveDirRecursive(FilePath) then
            Result := False;
        end
        else
        begin
          if not DeleteFile(FilePath) then
            Result := False;
        end;
      end;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;

  if not RemoveDir(DirName) then
    Result := False;
end;

procedure RemoveShortcuts();
var
  ProgramsPath, DesktopPath, PublicDesktop: String;
begin
  ProgramsPath := ExpandConstant('{commonprograms}') + '\' + TargetAppName;
  if DirExists(ProgramsPath) then
    RemoveDirRecursive(ProgramsPath);

  DesktopPath := ExpandConstant('{userdesktop}');
  if FileExists(DesktopPath + '\' + TargetAppName + '.lnk') then
    DeleteFile(DesktopPath + '\' + TargetAppName + '.lnk');

  PublicDesktop := ExpandConstant('{commondesktop}');
  if FileExists(PublicDesktop + '\' + TargetAppName + '.lnk') then
    DeleteFile(PublicDesktop + '\' + TargetAppName + '.lnk');
end;

function RunUninstall(): Boolean;
var
  UninstallCmd, UninstallExe, UninstallArgs: String;
  ResultCode: Integer;
  InstallLocation: String;
  DefaultDir: String;
begin
  Result := False;
  KillRunningApp();

  if FindUninstallString(UninstallCmd) then
  begin
    UninstallExe := RemoveQuotes(UninstallCmd);
    UninstallArgs := '';
    if Pos(' ', UninstallCmd) > 0 then
      UninstallArgs := Copy(UninstallCmd, Pos(' ', UninstallCmd) + 1, MaxInt);
    UninstallArgs := Trim(UninstallArgs + ' /VERYSILENT /NORESTART /SUPPRESSMSGBOXES');

    if Exec(UninstallExe, UninstallArgs, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      Result := True;
      Sleep(1500);
    end;
  end;

  if FindInstallLocation(InstallLocation) then
  begin
    InstallLocation := RemoveQuotes(InstallLocation);
    if (InstallLocation <> '') and DirExists(InstallLocation) then
      RemoveDirRecursive(InstallLocation);
  end;

  DefaultDir := ExpandConstant('{autopf}') + '\{#TargetFolder}';
  if DirExists(DefaultDir) then
    RemoveDirRecursive(DefaultDir);

  RemoveShortcuts();
  Result := True;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  WizardForm.Caption := TargetAppName + ' — 卸载旧版本';
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpReady then
  begin
    WizardForm.NextButton.Caption := SetupMessage(msgButtonInstall);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    WizardForm.NextButton.Enabled := False;
    try
      if RunUninstall() then
        MsgBox('卸载完成。' + #13#10 + #13#10 + '现在可以运行 ScreenCaptureSetup.exe 安装新版本。', mbInformation, MB_OK)
      else
        MsgBox('未能完成卸载，请尝试以管理员身份运行，或手动删除程序目录。', mbError, MB_OK);
    finally
      WizardForm.NextButton.Enabled := True;
    end;
    Result := False;
    WizardForm.Close;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = wpSelectDir then
    Result := True;
  if PageID = wpSelectProgramGroup then
    Result := True;
end;

procedure InitializeWizard();
begin
  WizardForm.LicenseAcceptedRadio.Checked := True;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  UninstallCmd, InstallLocation: String;
  Found: Boolean;
begin
  Found := FindUninstallString(UninstallCmd);
  FindInstallLocation(InstallLocation);

  Result := '即将卸载以下内容的旧版本：' + NewLine + NewLine;
  Result := Result + '程序名称：' + TargetAppName + NewLine;
  if Found then
    Result := Result + '安装记录：已找到（将调用官方卸载器）' + NewLine
  else
    Result := Result + '安装记录：未找到（将清理默认目录与快捷方式）' + NewLine;
  if InstallLocation <> '' then
    Result := Result + '安装目录：' + InstallLocation + NewLine
  else
    Result := Result + '默认目录：' + ExpandConstant('{autopf}') + '\{#TargetFolder}' + NewLine;
  Result := Result + NewLine + '点击「卸载」开始。卸载完成后请安装新版本。' + NewLine;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  { 不在 ssPostInstall 安装任何文件 }
end;
