@echo off
REM Resolves a usable uv into the UV_CMD variable for the caller.
REM Order: system uv on PATH -> local .uv copy -> download a local copy.
REM The caller must define UV_DIR (where to place a local copy).
REM This script intentionally does NOT use setlocal so UV_CMD reaches the caller.

set "UV_CMD="

where uv >nul 2>&1
if %errorlevel% equ 0 (
    set "UV_CMD=uv"
    goto :eof
)

if exist "%UV_DIR%\uv.exe" (
    set "UV_CMD=%UV_DIR%\uv.exe"
    goto :eof
)

echo [setup] uv が見つからないため自動取得します...
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell"
"%PS%" -ExecutionPolicy Bypass -NoProfile -Command "$env:UV_INSTALL_DIR='%UV_DIR%'; $env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex"

if exist "%UV_DIR%\uv.exe" (
    set "UV_CMD=%UV_DIR%\uv.exe"
)
goto :eof
