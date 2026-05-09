@echo off
title SysMonitorPro - Instalador Windows
color 0A

echo ===============================================
echo    SysMonitorPro - Instalador para Windows
echo ===============================================
echo.

:: Verificar Python
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no instalado
    echo Descargar desde: https://www.python.org/downloads/
    echo IMPORTANTE: Marcar "Add Python to PATH"
    pause
    exit /b 1
)
echo OK - Python encontrado
python --version
echo.

:: Verificar pip
echo [2/5] Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip no encontrado
    pause
    exit /b 1
)
echo OK - pip encontrado
echo.

:: Instalar dependencias
echo [3/5] Instalando dependencias...
pip install psutil
echo OK - psutil instalado
echo.

:: Preguntar por soporte de temperaturas
echo [4/5] Instalar soporte para temperaturas? (Recomendado)
echo Esto permite ver temperaturas de CPU/GPU
set /p instalar_temp="Instalar wmi y pywin32? (S/N): "
if /i "%instalar_temp%"=="S" (
    pip install wmi pywin32 GPUtil
    echo.
    echo IMPORTANTE: Para ver temperaturas necesitas:
    echo 1. Descargar OpenHardwareMonitor
    echo 2. Ejecutarlo (debe quedar abierto)
    echo 3. Link: https://openhardwaremonitor.org/
    echo.
) else (
    echo OK - Instalacion basica completada
    echo.
)

:: Crear directorio de configuracion
echo [5/5] Configurando archivos...
if not exist "%USERPROFILE%\.config\sysmonitorpro" mkdir "%USERPROFILE%\.config\sysmonitorpro"

:: Crear configuracion por defecto
if not exist "%USERPROFILE%\.config\sysmonitorpro\config.json" (
    echo {> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "intervalo": 1.0,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "mostrar_gpu": true,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "mostrar_discos": true,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "mostrar_red": true,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "mostrar_top": true,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "grafico_tamano": 40,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "historial_segundos": 60,>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo     "interfaz_red": "auto">> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo }>> "%USERPROFILE%\.config\sysmonitorpro\config.json"
    echo OK - Configuracion creada
) else (
    echo OK - Configuracion ya existe
)
echo.

:: Crear acceso directo en escritorio
set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop
if not exist "%DESKTOP%\SysMonitorPro.bat" (
    echo @echo off > "%DESKTOP%\SysMonitorPro.bat"
    echo cd /d "%SCRIPT_DIR%" >> "%DESKTOP%\SysMonitorPro.bat"
    echo python sysmonitorpro.py >> "%DESKTOP%\SysMonitorPro.bat"
    echo OK - Acceso directo creado en Escritorio
) else (
    echo OK - Acceso directo ya existe
)
echo.

:: Finalizar
echo ===============================================
echo    Instalacion completada con exito!
echo ===============================================
echo.
echo Para ejecutar:
echo   1. Abrir PowerShell o CMD en esta carpeta
echo   2. Escribir: python sysmonitorpro.py
echo   3. O hacer doble click en SysMonitorPro.bat del Escritorio
echo.
echo Para ver opciones:
echo   python sysmonitorpro.py --help
echo.
pause
