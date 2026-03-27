@echo off
setlocal

set ROOT_DIR=%~dp0
set ROOT_DIR=%ROOT_DIR:~0,-1%
set HOST=127.0.0.1
set PORT=8765
set URL=http://%HOST%:%PORT%

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>nul
if %ERRORLEVEL%==0 (
  start "" "%URL%"
  exit /b 0
)

cd /d "%ROOT_DIR%"
start "" "%URL%"
set PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%
python -m design_skill_miner serve --host %HOST% --port %PORT%
