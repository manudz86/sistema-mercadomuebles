@echo off
REM ============================================================================
REM INICIAR SISTEMA CANNON - VERSION MEJORADA
REM Muestra automáticamente la IP local
REM ============================================================================

title Sistema Cannon - Servidor
color 0A

echo ============================================================
echo   MERCADOMUEBLES - SISTEMA DE INVENTARIO
echo ============================================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Activar entorno virtual
echo [1/4] Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    color 0C
    echo.
    echo ERROR: No se encontro el entorno virtual
    echo.
    echo Soluciones:
    echo 1. Verifica que exista la carpeta 'venv'
    echo 2. Verifica que estas en la carpeta correcta
    echo.
    pause
    exit /b 1
)
echo      OK - Entorno virtual activado
echo.

REM Verificar que app.py exista
echo [2/4] Verificando archivos...
if not exist app.py (
    color 0C
    echo.
    echo ERROR: No se encontro app.py
    echo Verifica que estas en la carpeta correcta del proyecto
    echo.
    pause
    exit /b 1
)
echo      OK - Archivos encontrados
echo.

REM Obtener IP local
echo [3/4] Detectando IP local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP:~1%
echo      IP Local: %IP%
echo.

REM Iniciar Flask
echo [4/4] Iniciando servidor Flask...
echo.
echo ============================================================
echo   SISTEMA INICIADO CORRECTAMENTE
echo ============================================================
echo.
echo   Acceso local:  http://localhost:5000
echo   Acceso en red: http://%IP%:5000
echo.
echo   Las otras PCs deben acceder a: http://%IP%:5000
echo.
echo ============================================================
echo   Presiona Ctrl+C para DETENER el servidor
echo ============================================================
echo.

python app.py

REM Si se cierra, mostrar mensaje
echo.
color 0E
echo ============================================================
echo   SERVIDOR DETENIDO
echo ============================================================
echo.
pause
