@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  VoiceEmotionAvatar (VEA)
echo ========================================
echo.

REM uv を用意（無ければ .uv\ に自動取得）。Python と PyTorch は uv run が自動で揃える。
set "UV_DIR=%~dp0.uv"
call "%~dp0scripts\ensure_uv.bat"
if not defined UV_CMD (
    echo [ERROR] uv の準備に失敗しました。ネットワーク接続を確認してください。
    pause
    exit /b 1
)

echo 起動中... (初回は Python / PyTorch / モデルのダウンロードで時間がかかります)
echo.
"%UV_CMD%" run vea
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 実行中にエラーが発生しました。
    pause
    exit /b 1
)
