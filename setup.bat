@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  VoiceEmotionAvatar (VEA) Setup
echo ========================================
echo.
echo このスクリプトは依存環境を事前に準備します（任意）。
echo そのまま起動したい場合は start.bat をダブルクリックするだけで構いません。
echo.

REM uv を用意（無ければ .uv\ に自動取得）。
set "UV_DIR=%~dp0.uv"
call "%~dp0scripts\ensure_uv.bat"
if not defined UV_CMD (
    echo [ERROR] uv の準備に失敗しました。ネットワーク接続を確認してください。
    pause
    exit /b 1
)

echo [1/2] 依存パッケージをインストール中... (初回は PyTorch 等のDLで時間がかかります)
"%UV_CMD%" sync
if %errorlevel% neq 0 (
    echo [ERROR] 依存パッケージのインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo [2/2] セットアップ完了!
echo   起動するには start.bat を実行してください。
echo.
pause
