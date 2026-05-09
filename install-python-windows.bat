@echo off
title Instalador Automático de Python para SysMonitorPro
color 0A

echo ===============================================
echo    Instalador de Python y dependencias
echo         para SysMonitorPro en Windows
echo ===============================================
echo.

:: Verificar si Python ya está instalado
python --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] Python ya esta instalado
    python --version
    goto :instalar_pip
)

echo [INFO] Python no encontrado. Instalando...
echo.

:: Descargar Python usando winget (recomendado)
echo Descargando Python desde Microsoft Store...
winget install Python.Python.3.12 --accept-package-agreements --silent

if errorlevel 1 (
    echo [ERROR] No se pudo instalar Python automaticamente
    echo.
    echo Instalacion manual requerida:
    echo 1. Ir a: https://www.python.org/downloads/
    echo 2. Descargar Python 3.12
    echo 3. Ejecutar el instalador
    echo 4. MARCAR "Add Python to PATH"
    echo 5. Cerrar esta ventana
    echo 6. Volver a ejecutar este script
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Python instalado correctamente
echo.

:instalar_pip
:: Verificar pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip no encontrado
    echo Instalando pip...
    python -m ensurepip --upgrade
)

:: Instalar dependencias principales
echo.
echo [1/3] Instalando psutil...
python -m pip install psutil

:: Instalar dependencias opcionales
echo.
set /p instalar_temp="Instalar soporte para temperaturas? (S/N): "
if /i "%instalar_temp%"=="S" (
    echo [2/3] Instalando wmi, pywin32, GPUtil...
    python -m pip install wmi pywin32 GPUtil
    echo.
    echo IMPORTANTE: Para ver temperaturas necesitas:
    echo 1. Descargar OpenHardwareMonitor
    echo 2. Link: https://openhardwaremonitor.org/
    echo 3. Ejecutarlo (debe quedar abierto)
) else (
    echo [2/3] Saltando instalacion de temperaturas
)

:: Verificar instalacion
echo.
echo [3/3] Verificando instalacion...
python -c "import psutil" >nul 2>&1
if not errorlevel 1 (
    echo [OK] psutil instalado correctamente
) else (
    echo [ERROR] psutil no se instalo correctamente
)

:: Finalizar
echo.
echo ===============================================
echo    Instalacion completada con exito!
echo ===============================================
echo.
echo Para ejecutar SysMonitorPro:
echo   1. Navegar a la carpeta del proyecto
echo   2. Ejecutar: python sysmonitorpro.py
echo.
pause
