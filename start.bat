@echo off
echo ========================================
echo  VoiceEmotionAvatar (VEA)
echo ========================================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv が見つかりません。先に setup.bat を実行してください。
    pause
    exit /b 1
)

echo 起動中... (初回はモデルダウンロードに時間がかかります)
echo.
uv run vea
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 実行中にエラーが発生しました。
    pause
    exit /b 1
)
