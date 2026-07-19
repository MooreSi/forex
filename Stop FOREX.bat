@echo off
echo.
echo  FOREX Trader — Stopping...
echo.

:: Kill any process listening on port 8888 (NiceGUI app)
set "FOUND8888=0"
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo  Stopped app process PID %%p (port 8888)
    set "FOUND8888=1"
)
if "!FOUND8888!"=="0" echo  App (port 8888): not running

:: Kill any process listening on port 9000 (MT5 bridge)
set "FOUND9000=0"
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":9000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo  Stopped bridge process PID %%p (port 9000)
    set "FOUND9000=1"
)
if "!FOUND9000!"=="0" echo  Bridge (port 9000): not running

echo.
echo  Done.
timeout /t 3 /nobreak >nul
