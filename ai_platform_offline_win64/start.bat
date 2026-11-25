@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo [错误] 尚未安装，请先运行 install.bat
  pause
  exit /b 1
)
echo 启动中：http://127.0.0.1:8000  （Ctrl+C 停止）
REM 3 秒后自动打开浏览器
start cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
