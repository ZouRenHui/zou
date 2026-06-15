@echo off
chcp 65001 >nul
title 录屏截屏工具 — 卸载

set "SCRIPT=%~dp0scripts\uninstall.ps1"
if not exist "%SCRIPT%" (
    echo 未找到卸载脚本: %SCRIPT%
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
exit /b %ERRORLEVEL%
