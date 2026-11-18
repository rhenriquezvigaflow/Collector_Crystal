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
    echo ERROR: Could not activate the virtual environment
    exit /b 1
)

REM Archivo de configuracion MASTER
set CONFIG_FILE=%BASE_DIR%collectors.yml

if not exist "%CONFIG_FILE%" (
    echo ERROR: Configuration file not found:
    echo   %CONFIG_FILE%
    exit /b 1
)

echo Using configuration:
echo   %CONFIG_FILE%
echo.

REM ==========================
REM ARRANQUE DIRECTO
REM ==========================
echo Starting collector (direct mode)...
echo.

python "%BASE_DIR%main.py" --config "%CONFIG_FILE%"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo Collector exited with code: %EXIT_CODE%
echo.

REM ==========================
REM FALLBACK A SUPERVISOR
REM ==========================
if NOT "%EXIT_CODE%"=="0" (
    echo ==========================================
    echo Collector failed. Starting SUPERVISOR...
    echo ==========================================
    echo.

    python "%BASE_DIR%supervisor.py"
)

echo.
echo Process finished.
