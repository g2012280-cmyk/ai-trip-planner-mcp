@echo off
echo 清理旧进程...
powershell -Command "Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
powershell -Command "Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul

cd /d "%~dp0backend"
start cmd /k "uvicorn app.main:app --port 8001"
cd /d "%~dp0frontend"
start cmd /k "npm run dev"
timeout /t 3 /nobreak >nul
start http://localhost:5173
