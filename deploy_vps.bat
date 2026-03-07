@echo off
echo.
echo ========================================
echo   DEPLOY SISTEMA CANNON - VPS
echo ========================================
echo.

set /p MENSAJE="Mensaje del commit: "
if "%MENSAJE%"=="" set MENSAJE=deploy %date% %time%

echo [1/3] Pusheando cambios a GitHub...
cd /d "C:\Users\manud\Downloads\sistema cannon SIMPLE\sistema_cannon_simple"
git add .
git commit -m "%MENSAJE%"
git push
if %errorlevel% neq 0 (
    echo ERROR en git push
    pause
    exit /b 1
)

echo.
echo [2/3] Aplicando cambios en el VPS...
ssh root@72.61.134.243 "cd /home/cannon/app && git pull && systemctl restart cannon"
if %errorlevel% neq 0 (
    echo ERROR conectando al VPS
    pause
    exit /b 1
)

echo.
echo [3/3] Verificando estado...
ssh root@72.61.134.243 "systemctl status cannon --no-pager | head -5"

echo.
echo ========================================
echo   DEPLOY COMPLETADO OK
echo ========================================
echo.
pause
