@echo off
echo ========================================
echo  VoiceEmotionAvatar (VEA) Setup
echo ========================================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv が見つかりません。
    echo   https://docs.astral.sh/uv/getting-started/installation/
    echo   からインストールしてください。
    pause
    exit /b 1
)

echo [1/2] 依存パッケージをインストール中...
uv sync
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
