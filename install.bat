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

:: === 4. SENSORES (DISCOS, GPU, TEMPERATURAS) ===
:: wmi y pywin32 son necesarios para listar discos fisicos, GPU y leer
:: LibreHardwareMonitor. GPUtil ya no se instala: no funciona en Python 3.12+.
echo [4/8] Instalando soporte de sensores (wmi, pywin32)...
pip install wmi pywin32
if errorlevel 1 (
    echo [AVISO] No se pudo instalar wmi/pywin32: discos y GPU se veran con menos detalle
) else (
    echo [OK] Soporte de sensores instalado
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
    echo     "mostrar_fps": true,>> "%CONFIG_DIR%\config.json"
    echo     "interfaz_red": "auto">> "%CONFIG_DIR%\config.json"
    echo }>> "%CONFIG_DIR%\config.json"
    echo [OK] Configuracion creada en %CONFIG_DIR%\config.json
) else (
    echo [OK] Configuracion ya existe
)
echo.

:: === 6. CREAR LANZADOR .BAT ===
:: Se regenera siempre: versiones anteriores lo creaban sin pausa y la
:: ventana se cerraba sin mostrar el error.
echo [6/8] Creando lanzador...
> "%SCRIPT_DIR%sysmonitor.bat" echo @echo off
>> "%SCRIPT_DIR%sysmonitor.bat" echo cd /d "%%~dp0"
>> "%SCRIPT_DIR%sysmonitor.bat" echo python sysmonitorpro.py %%*
>> "%SCRIPT_DIR%sysmonitor.bat" echo if errorlevel 1 pause
echo [OK] Lanzador creado: sysmonitor.bat
echo.

:: === 7. ICONO ===
:: icon.ico viene incluido en el repositorio (el base64 que se generaba antes
:: estaba corrupto y Windows mostraba el acceso directo sin icono).
echo [7/8] Verificando icono...
if exist "%SCRIPT_DIR%icon.ico" (
    echo [OK] Icono: icon.ico
) else (
    echo [AVISO] No se encontro icon.ico, se usara el icono por defecto
)
echo.

:: === 8. CREAR ACCESO DIRECTO (ESCRITORIO + MENU INICIO) ===
echo [8/8] Configurando acceso directo...
set /p crear_acceso="[?] Crear acceso directo en el escritorio y menu Inicio? (S/N): "
if /i not "%crear_acceso%"=="S" goto :sin_acceso

:: Las rutas se pasan por variables de entorno para no romper comillas con
:: espacios, acentos o parentesis. GetFolderPath('Desktop') respeta el
:: escritorio redirigido a OneDrive (antes se asumia %USERPROFILE%\Desktop).
set "SM_DIR=%SCRIPT_DIR:~0,-1%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w = New-Object -ComObject WScript.Shell;" ^
  "$ok = $true;" ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  try {" ^
  "    $l = $w.CreateShortcut((Join-Path $dir 'SysMonitorPro.lnk'));" ^
  "    $l.TargetPath = Join-Path $env:SM_DIR 'sysmonitor.bat';" ^
  "    $l.WorkingDirectory = $env:SM_DIR;" ^
  "    $ico = Join-Path $env:SM_DIR 'icon.ico';" ^
  "    if (Test-Path $ico) { $l.IconLocation = $ico + ',0' };" ^
  "    $l.Description = 'Monitor de sistema avanzado';" ^
  "    $l.Save();" ^
  "    Write-Host ('[OK] Acceso directo: ' + (Join-Path $dir 'SysMonitorPro.lnk'))" ^
  "  } catch { Write-Host ('[ERROR] ' + $_.Exception.Message); $ok = $false }" ^
  "};" ^
  "if (-not $ok) { exit 1 }"
if errorlevel 1 (
    echo [ERROR] No se pudo crear el acceso directo
)

:sin_acceso
echo.

:: === LIMPIEZA DE ARCHIVOS INNECESARIOS ===
echo [INFO] Limpiando archivos innecesarios...
if exist "%SCRIPT_DIR%install.sh" del /q "%SCRIPT_DIR%install.sh" 2>nul
if exist "%SCRIPT_DIR%uninstall.sh" del /q "%SCRIPT_DIR%uninstall.sh" 2>nul
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
