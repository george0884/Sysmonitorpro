@echo off
title SysMonitorPro - Desinstalador Interactivo (Windows)
color 0C

echo =================================================
echo    SysMonitorPro - Desinstalador Interactivo
echo =================================================
echo.
echo ADVERTENCIA: Este script eliminara componentes de SysMonitorPro.
echo Te preguntaremos ANTES de eliminar cada cosa.
echo.
set /p continuar="¿Deseas continuar con la desinstalacion? (S/N): "
if /i not "%continuar%"=="S" (
    echo Operacion cancelada. No se elimino nada.
    exit /b 0
)

:: === 1. ELIMINAR LANZADOR .BAT ===
if exist "sysmonitor.bat" (
    echo.
    echo [DETECTADO] Lanzador local: sysmonitor.bat
    set /p eliminar_bat="¿Deseas eliminar este lanzador? (S/N): "
    if /i "!eliminar_bat!"=="S" (
        del /q sysmonitor.bat 2>nul
        echo [OK] Lanzador .bat eliminado.
    ) else (
        echo [INFO] Lanzador conservado.
    )
)

:: === 2. ELIMINAR ENTORNO VIRTUAL ===
if exist "venv\" (
    echo.
    echo [DETECTADO] Entorno virtual: venv/
    set /p eliminar_venv="¿Deseas eliminar el entorno virtual? (S/N): "
    if /i "!eliminar_venv!"=="S" (
        rmdir /s /q venv 2>nul
        echo [OK] Entorno virtual eliminado.
    ) else (
        echo [INFO] Entorno virtual conservado.
    )
)

:: === 3. ELIMINAR CARPETA DE CONFIGURACION DEL USUARIO ===
set CONFIG_DIR=%USERPROFILE%\.config\sysmonitorpro
if exist "%CONFIG_DIR%\" (
    echo.
    echo [DETECTADO] Carpeta de configuracion: %CONFIG_DIR%
    set /p eliminar_config="¿Deseas eliminar TODA la configuracion? (S/N): "
    if /i "!eliminar_config!"=="S" (
        rmdir /s /q "%CONFIG_DIR%" 2>nul
        echo [OK] Configuracion eliminada.
    ) else (
        echo [INFO] Configuracion conservada.
    )
)

:: === 4. ELIMINAR DEPENDENCIAS DE PYTHON ===
echo.
echo [BUSCANDO] Paquetes de Python instalados por SysMonitorPro...
set PAQUETES=psutil gputil wmi pywin32
set PAQUETES_INSTALADOS=

for %%p in (%PAQUETES%) do (
    pip show %%p >nul 2>&1
    if not errorlevel 1 (
        echo    - %%p (instalado)
        set "PAQUETES_INSTALADOS=!PAQUETES_INSTALADOS! %%p"
    )
)

if defined PAQUETES_INSTALADOS (
    echo.
    set /p eliminar_pip="¿Deseas desinstalar estos paquetes? (S/N): "
    if /i "!eliminar_pip!"=="S" (
        for %%p in (!PAQUETES_INSTALADOS!) do (
            echo    Desinstalando %%p...
            pip uninstall -y %%p >nul 2>&1
        )
        echo [OK] Paquetes de Python eliminados.
    ) else (
        echo [INFO] Paquetes conservados.
    )
) else (
    echo [INFO] No se encontraron paquetes.
)

:: === 5. ELIMINAR RESIDUOS DE COMPILACION ===
if exist "build\" set HAY_BUILD=1
if exist "dist\" set HAY_DIST=1
if exist "*.spec" set HAY_SPEC=1

if defined HAY_BUILD set HAY_RESIDUOS=1
if defined HAY_DIST set HAY_RESIDUOS=1
if defined HAY_SPEC set HAY_RESIDUOS=1

if defined HAY_RESIDUOS (
    echo.
    set /p eliminar_residuos="¿Deseas eliminar residuos de compilacion (build, dist, *.spec)? (S/N): "
    if /i "!eliminar_residuos!"=="S" (
        if defined HAY_BUILD rmdir /s /q build 2>nul
        if defined HAY_DIST rmdir /s /q dist 2>nul
        if defined HAY_SPEC del /q *.spec 2>nul
        echo [OK] Residuos eliminados.
    ) else (
        echo [INFO] Residuos conservados.
    )
) else (
    echo [INFO] No se encontraron residuos.
)

:: === 6. ELIMINAR OPENHARDWAREMONITOR (SOLO SI EL USUARIO LO PIDE) ===
if exist "C:\Program Files\OpenHardwareMonitor\OpenHardwareMonitor.exe" (
    echo.
    echo [ATENCION] Se detecto OpenHardwareMonitor instalado en el sistema.
    echo    Esto NO es parte de SysMonitorPro, pero se recomendo durante la instalacion.
    set /p eliminar_ohm="¿Deseas eliminar OpenHardwareMonitor del sistema? (S/N): "
    if /i "!eliminar_ohm!"=="S" (
        echo Eliminando OpenHardwareMonitor...
        if exist "C:\Program Files\OpenHardwareMonitor\Uninstall.exe" (
            start /wait "" "C:\Program Files\OpenHardwareMonitor\Uninstall.exe" /S
        ) else (
            rmdir /s /q "C:\Program Files\OpenHardwareMonitor" 2>nul
        )
        echo [OK] OpenHardwareMonitor eliminado.
    ) else (
        echo [INFO] OpenHardwareMonitor conservado.
    )
)

:: === 7. ELIMINAR CARPETA DEL PROGRAMA ===
echo.
echo [PREGUNTA] ¿Deseas eliminar tambien la carpeta completa del proyecto?
echo    (Ubicacion actual: %CD%)
set /p eliminar_repo="¿Eliminar TODA esta carpeta? (S/N): "
if /i "!eliminar_repo!"=="S" (
    cd ..
    echo Eliminando repositorio...
    rmdir /s /q "%~dp0" 2>nul
    echo [OK] Repositorio eliminado.
    echo [INFO] La terminal se cerrara en 5 segundos...
    timeout /t 5 /nobreak >nul
    exit /b 0
) else (
    echo [INFO] Repositorio conservado.
)

echo.
echo =================================================
echo    Desinstalacion completada. Sistema limpio.
echo =================================================
pause
