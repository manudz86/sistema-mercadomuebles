@echo off
echo ========================================
echo Reiniciando Sistema Cannon
echo ========================================
echo.

echo [1/3] Buscando proceso Flask en ejecucion...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do (
    echo Deteniendo proceso %%a
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo [2/3] Cambiando al directorio del sistema...
cd /d "%~dp0"

echo [3/3] Iniciando servidor Flask...
echo.
echo ========================================
echo Sistema iniciado en http://localhost:5000
echo Presiona Ctrl+C para detener
echo ========================================
echo.

python app.py

pause
