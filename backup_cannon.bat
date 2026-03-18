@echo off
set FECHA=%date:~6,4%-%date:~3,2%-%date:~0,2%
set ARCHIVO="C:\Users\manud\OneDrive\Backup sistema\backup_cannon_%FECHA%.sql"

echo Haciendo backup de inventario_cannon desde VPS...

ssh root@72.61.134.243 "mysqldump -u cannon -pSistema@32267845 inventario_cannon" > %ARCHIVO%

if errorlevel 1 (
    echo ERROR: Fallo el backup.
    pause
    exit /b 1
)

echo.
echo Backup completado exitosamente!
echo Archivo: %ARCHIVO%
echo.
pause
