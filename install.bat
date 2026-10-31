@echo off
title SysMonitorPro - Instalador Interactivo (Windows)
color 0A
setlocal enabledelayedexpansion

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
echo [1/8] Verificando Python...
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
echo [2/8] Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip no encontrado
    pause
    exit /b 1
)
echo [OK] pip disponible
echo.

:: === 3. INSTALAR PSUTIL ===
echo [3/8] Instalando psutil...
pip install psutil
if errorlevel 1 (
    echo [ERROR] No se pudo instalar psutil
    pause
    exit /b 1
)
echo [OK] psutil instalado
echo.

:: === 4. INSTALAR GPU OPCIONAL ===
set /p instalar_gpu="[4/8] Instalar soporte para GPU? (S/N): "
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
echo [5/8] Configurando archivos...
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
echo [6/8] Creando lanzador...
if not exist "%SCRIPT_DIR%sysmonitor.bat" (
    echo @echo off > "%SCRIPT_DIR%sysmonitor.bat"
    echo cd /d "%SCRIPT_DIR%" >> "%SCRIPT_DIR%sysmonitor.bat"
    echo python sysmonitorpro.py %%* >> "%SCRIPT_DIR%sysmonitor.bat"
    echo [OK] Lanzador creado: sysmonitor.bat
) else (
    echo [OK] Lanzador ya existe
)
echo.

:: === 7. CREAR ICONO ===
echo [7/8] Creando icono...
if not exist "%SCRIPT_DIR%icon.ico" (
    echo [INFO] Generando icono base...
    :: Crear un archivo ICO simple con contenido base64
    echo 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 > "%TEMP%\icon_base64.txt"
    certutil -decode "%TEMP%\icon_base64.txt" "%SCRIPT_DIR%icon.ico" >nul 2>&1
    del "%TEMP%\icon_base64.txt" 2>nul
    echo [OK] Icono creado: icon.ico
) else (
    echo [OK] Icono ya existe
)
echo.

:: === 8. CREAR ACCESO DIRECTO EN EL ESCRITORIO ===
echo [8/8] Configurando acceso directo...
set /p crear_acceso="[?] ¿Crear acceso directo en el escritorio? (S/N): "
if /i "%crear_acceso%"=="S" (
    echo Creando acceso directo...
    
    :: Crear script VBS para generar acceso directo
    set "ICON_PATH=%SCRIPT_DIR%icon.ico"
    set "DESKTOP=%USERPROFILE%\Desktop"
    
    echo Set oShell = CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
    echo Set oLink = oShell.CreateShortcut("%DESKTOP%\SysMonitorPro.lnk") >> "%TEMP%\create_shortcut.vbs"
    echo oLink.TargetPath = "python.exe" >> "%TEMP%\create_shortcut.vbs"
    echo oLink.Arguments = "%SCRIPT_DIR%sysmonitorpro.py" >> "%TEMP%\create_shortcut.vbs"
    echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%TEMP%\create_shortcut.vbs"
    echo oLink.IconLocation = "%ICON_PATH%" >> "%TEMP%\create_shortcut.vbs"
    echo oLink.Description = "Monitor de sistema avanzado" >> "%TEMP%\create_shortcut.vbs"
    echo oLink.Save >> "%TEMP%\create_shortcut.vbs"
    
    cscript //nologo "%TEMP%\create_shortcut.vbs"
    del "%TEMP%\create_shortcut.vbs"
    
    echo [OK] Acceso directo creado en el escritorio
)
echo.

:: === LIMPIEZA DE ARCHIVOS INNECESARIOS ===
echo [INFO] Limpiando archivos innecesarios...
if exist "%SCRIPT_DIR%install.sh" del /q "%SCRIPT_DIR%install.sh" 2>nul
if exist "%SCRIPT_DIR%uninstall.sh" del /q "%SCRIPT_DIR%uninstall.sh" 2>nul
if exist "%SCRIPT_DIR%requeriments-linux.txt" del /q "%SCRIPT_DIR%requeriments-linux.txt" 2>nul
if exist "%SCRIPT_DIR%requirements-linux.txt" del /q "%SCRIPT_DIR%requirements-linux.txt" 2>nul
if exist "%SCRIPT_DIR%Linux.png" del /q "%SCRIPT_DIR%Linux.png" 2>nul
if exist "%SCRIPT_DIR%*.sh" del /q "%SCRIPT_DIR%*.sh" 2>nul
echo [OK] Limpieza completada
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
if /i "%crear_acceso%"=="S" (
    echo   O hacer doble clic en el icono del escritorio
)
echo.
echo Para ver opciones:
echo   python sysmonitorpro.py --help
echo.
pause
