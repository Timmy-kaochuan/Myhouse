@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  重型燃机集成设计平台 - 离线安装（无需联网）
echo ============================================

REM 优先使用 py 启动器，找不到则用 python
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
echo 使用解释器: %PY%
%PY% --version || (echo [错误] 未找到 Python 3.10+，请先安装 & pause & exit /b 1)

echo.
echo [1/3] 创建虚拟环境 .venv ...
%PY% -m venv .venv

echo [2/3] 从本地 wheels 目录离线安装依赖（不访问网络）...
.venv\Scripts\python -m pip install --no-index --find-links wheels -r requirements.txt
if errorlevel 1 (echo [错误] 依赖安装失败，请确认 Python 版本为 3.10~3.13 & pause & exit /b 1)

echo [3/3] 初始化数据库（SQLite：ai_platform.db）...
.venv\Scripts\alembic upgrade head
if errorlevel 1 (echo [错误] 数据库初始化失败 & pause & exit /b 1)

echo.
echo ============================================
echo  安装完成！双击 start.bat 启动平台
echo ============================================
pause
