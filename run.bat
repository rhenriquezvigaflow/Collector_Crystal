@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM ==========================================
REM Crystal Lagoons - Collector SCADA
REM ==========================================

REM Directorio base (donde está este .bat)
set BASE_DIR=%~dp0

echo ==========================================
echo Crystal Lagoons - Collector
echo ==========================================
echo Base dir: %BASE_DIR%
echo.

REM Activar entorno virtual
call "%BASE_DIR%.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: No se pudo activar el entorno virtual
    pause
    exit /b 1
)

REM Archivo de configuracion MASTER
set CONFIG_FILE=%BASE_DIR%collectors.yml

if not exist "%CONFIG_FILE%" (
    echo ERROR: No se encontro el archivo:
    echo   %CONFIG_FILE%
    pause
    exit /b 1
)

echo Usando configuracion:
echo   %CONFIG_FILE%
echo.

REM ==========================
REM ARRANQUE DIRECTO
REM ==========================
echo Iniciando collector (modo directo)...
echo.

python "%BASE_DIR%main.py" --config "%CONFIG_FILE%"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo Collector termino con codigo: %EXIT_CODE%
echo.

REM ==========================
REM FALLBACK A SUPERVISOR
REM ==========================
if NOT "%EXIT_CODE%"=="0" (
    echo ==========================================
    echo Collector fallo. Iniciando SUPERVISOR...
    echo ==========================================
    echo.

    python "%BASE_DIR%supervisor.py"
)

echo.
echo Proceso finalizado.
pause
