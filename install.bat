@echo off
title SysMonitorPro - Instalador Interactivo (Windows)
color 0A

echo =================================================
echo    SysMonitorPro - Instalador Interactivo
echo =================================================
echo.

:: === DETECTAR CARPETA DEL SCRIPT ===
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [INFO] Carpeta del proyecto: %SCRIPT_DIR%
echo.

:: === 1. VERIFICAR PYTHON ===
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no instalado.
    echo        Descargar desde: https://www.python.org/downloads/
    echo        IMPORTANTE: Marcar "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] Python encontrado
python --version
echo.

:: === 2. VERIFICAR PIP ===
echo [2/6] Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip no encontrado
    pause
    exit /b 1
)
echo [OK] pip disponible
echo.

:: === 3. INSTALAR PSUTIL ===
echo [3/6] Instalando psutil...
pip install psutil
if errorlevel 1 (
    echo [ERROR] No se pudo instalar psutil
    pause
    exit /b 1
)
echo [OK] psutil instalado
echo.

:: === 4. INSTALAR GPU OPCIONAL ===
set /p instalar_gpu="[4/6] Instalar soporte para GPU? (S/N): "
if /i "%instalar_gpu%"=="S" (
    echo Instalando GPUtil...
    pip install gputil
    echo Instalando wmi y pywin32...
    pip install wmi pywin32
    echo [OK] Soporte GPU instalado
) else (
    echo [INFO] Soporte GPU omitido
)
echo.

:: === 5. CREAR CONFIGURACION ===
echo [5/6] Configurando archivos...
set CONFIG_DIR=%USERPROFILE%\.config\sysmonitorpro
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%CONFIG_DIR%\config.json" (
    echo {> "%CONFIG_DIR%\config.json"
    echo     "intervalo": 1.0,>> "%CONFIG_DIR%\config.json"
    echo     "mostrar_gpu": true,>> "%CONFIG_DIR%\config.json"
    echo     "mostrar_discos": true,>> "%CONFIG_DIR%\config.json"
    echo     "mostrar_red": true,>> "%CONFIG_DIR%\config.json"
    echo     "mostrar_top": true,>> "%CONFIG_DIR%\config.json"
    echo     "grafico_tamano": 40,>> "%CONFIG_DIR%\config.json"
    echo     "historial_segundos": 60,>> "%CONFIG_DIR%\config.json"
    echo     "interfaz_red": "auto">> "%CONFIG_DIR%\config.json"
    echo }>> "%CONFIG_DIR%\config.json"
    echo [OK] Configuracion creada en %CONFIG_DIR%\config.json
) else (
    echo [OK] Configuracion ya existe
)
echo.

:: === 6. CREAR LANZADOR .BAT ===
echo [6/6] Creando lanzador...
if not exist "%SCRIPT_DIR%sysmonitor.bat" (
    echo @echo off > "%SCRIPT_DIR%sysmonitor.bat"
    echo cd /d "%SCRIPT_DIR%" >> "%SCRIPT_DIR%sysmonitor.bat"
    echo python sysmonitorpro.py %%* >> "%SCRIPT_DIR%sysmonitor.bat"
    echo [OK] Lanzador creado: sysmonitor.bat
) else (
    echo [OK] Lanzador ya existe
)
echo.

:: === PRUEBA RAPIDA ===
echo Probando instalacion...
python -c "import psutil" >nul 2>&1
if not errorlevel 1 (
    echo [OK] Todo funciona correctamente
) else (
    echo [ERROR] Error en la prueba
)

:: === FINAL ===
echo.
echo =================================================
echo    Instalacion completada con exito!
echo =================================================
echo.
echo Para ejecutar:
echo   python sysmonitorpro.py
echo   O usar: sysmonitor.bat
echo.
echo Para ver opciones:
echo   python sysmonitorpro.py --help
echo.
pause
