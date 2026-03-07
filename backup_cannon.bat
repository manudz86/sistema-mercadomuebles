@echo off
set FECHA=%date:~6,4%-%date:~3,2%-%date:~0,2%
set ARCHIVO="C:\Users\manud\OneDrive\Backup sistema\backup_cannon_%FECHA%.sql"
set MYSQL="C:\Program Files\MySQL\MySQL Workbench 8.0\mysql.exe"

echo Haciendo backup de inventario_cannon...
%MYSQL% -h nozomi.proxy.rlwy.net -P 47691 -u root -pKuphtnvZCyijflqkKATGphKtdenxowGD --skip-column-names -e "SELECT 1" > nul 2>&1

if errorlevel 1 (
    echo ERROR: No se pudo conectar a la base de datos.
    pause
    exit /b 1
)

"C:\Program Files\MySQL\MySQL Workbench 8.0\mysqldump.exe" -h nozomi.proxy.rlwy.net -P 47691 -u root -pKuphtnvZCyijflqkKATGphKtdenxowGD inventario_cannon > %ARCHIVO%

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
