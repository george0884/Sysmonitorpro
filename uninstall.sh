#!/bin/bash
# uninstall.sh - Desinstalador interactivo seguro para SysMonitorPro
# No elimina nada sin preguntar.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'
D='\033[2m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${RED}   SysMonitorPro - Desinstalador Interactivo${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠️  ATENCIÓN: Este script eliminará componentes de SysMonitorPro.${NC}"
echo -e "${YELLOW}⚠️  Te preguntaremos ANTES de eliminar cada cosa.${NC}"
echo ""
read -p "¿Deseas continuar con la desinstalación? (s/N): " -r continuar
if [[ ! $continuar =~ ^[Ss]$ ]]; then
    echo -e "${GREEN}Operación cancelada. No se eliminó nada.${NC}"
    exit 0
fi

# === 1. ELIMINAR COMANDO GLOBAL (sysmonitor) ===
if command -v sysmonitor &> /dev/null; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó el comando global 'sysmonitor' en /usr/local/bin/sysmonitor${NC}"
    read -p "¿Deseas eliminar este comando global? (s/N): " -r eliminar_comando
    if [[ $eliminar_comando =~ ^[Ss]$ ]]; then
        sudo rm -f /usr/local/bin/sysmonitor
        echo -e "${GREEN}✓ Comando global 'sysmonitor' eliminado.${NC}"
    else
        echo -e "${D}➜ Comando global conservado.${NC}"
    fi
else
    echo -e "${D}➜ No se encontró el comando global 'sysmonitor'. Saltando...${NC}"
fi

# === 2. ELIMINAR LANZADOR LOCAL (./sysmonitor) ===
if [ -f "sysmonitor" ]; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó el lanzador local './sysmonitor'${NC}"
    read -p "¿Deseas eliminar este lanzador local? (s/N): " -r eliminar_lanzador
    if [[ $eliminar_lanzador =~ ^[Ss]$ ]]; then
        rm -f sysmonitor
        echo -e "${GREEN}✓ Lanzador local eliminado.${NC}"
    else
        echo -e "${D}➜ Lanzador local conservado.${NC}"
    fi
fi

# === 3. ELIMINAR ENTORNO VIRTUAL ===
if [ -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó el entorno virtual 'venv' (${BOLD}$(du -sh venv | cut -f1)${NC}${YELLOW})${NC}"
    read -p "¿Deseas eliminar este entorno virtual? (s/N): " -r eliminar_venv
    if [[ $eliminar_venv =~ ^[Ss]$ ]]; then
        rm -rf venv
        echo -e "${GREEN}✓ Entorno virtual eliminado.${NC}"
    else
        echo -e "${D}➜ Entorno virtual conservado.${NC}"
    fi
fi

# === 4. ELIMINAR CARPETA DE CONFIGURACIÓN DEL USUARIO ===
CONFIG_DIR="$HOME/.config/sysmonitorpro"
if [ -d "$CONFIG_DIR" ]; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó la carpeta de configuración del usuario:${NC} ${BOLD}$CONFIG_DIR${NC}"
    echo -e "${YELLOW}   (Contiene config.json y preferencias personales)${NC}"
    read -p "¿Deseas eliminar TODA la configuración de SysMonitorPro? (s/N): " -r eliminar_config
    if [[ $eliminar_config =~ ^[Ss]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✓ Carpeta de configuración eliminada.${NC}"
    else
        echo -e "${D}➜ Configuración conservada.${NC}"
    fi
fi

# === 5. ELIMINAR DEPENDENCIAS DE PYTHON (psutil, gputil, pyamdgpuinfo) ===
echo ""
echo -e "${YELLOW}🔍 Buscando paquetes de Python instalados por SysMonitorPro...${NC}"
PAQUETES_PYTHON=("psutil" "gputil" "pyamdgpuinfo")
PAQUETES_A_ELIMINAR=()

for paquete in "${PAQUETES_PYTHON[@]}"; do
    if pip3 show "$paquete" &> /dev/null; then
        echo -e "   - ${BOLD}$paquete${NC} (instalado)"
        PAQUETES_A_ELIMINAR+=("$paquete")
    fi
done

if [ ${#PAQUETES_A_ELIMINAR[@]} -gt 0 ]; then
    echo ""
    read -p "¿Deseas desinstalar estos paquetes de Python? (s/N): " -r eliminar_pip
    if [[ $eliminar_pip =~ ^[Ss]$ ]]; then
        for paquete in "${PAQUETES_A_ELIMINAR[@]}"; do
            echo -e "${YELLOW}   Desinstalando $paquete...${NC}"
            pip3 uninstall -y "$paquete" 2>/dev/null || pip uninstall -y "$paquete" 2>/dev/null
        done
        echo -e "${GREEN}✓ Paquetes de Python eliminados.${NC}"
    else
        echo -e "${D}➜ Paquetes de Python conservados.${NC}"
    fi
else
    echo -e "${D}➜ No se encontraron paquetes de Python instalados por este proyecto.${NC}"
fi

# === 6. ELIMINAR RESIDUOS DE COMPILACIÓN (AppImage, build, dist) ===
echo ""
echo -e "${YELLOW}🔍 Buscando residuos de compilación...${NC}"
if [ -d "build" ] || [ -d "dist" ] || ls *.spec &> /dev/null; then
    echo -e "${YELLOW}   Se detectaron carpetas: build, dist o archivos .spec${NC}"
    read -p "¿Deseas eliminar estos residuos de compilación? (s/N): " -r eliminar_residuos
    if [[ $eliminar_residuos =~ ^[Ss]$ ]]; then
        rm -rf build dist *.spec 2>/dev/null
        rm -f *.AppImage 2>/dev/null
        echo -e "${GREEN}✓ Residuos de compilación eliminados.${NC}"
    else
        echo -e "${D}➜ Residuos conservados.${NC}"
    fi
fi

# === 7. ELIMINAR OPENHARDWAREMONITOR (SOLO WINDOWS, PREGUNTA EXPLÍCITA) ===
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    if [ -d "C:/Program Files/OpenHardwareMonitor" ] || [ -f "C:/Program Files/OpenHardwareMonitor/OpenHardwareMonitor.exe" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  ¡CUIDADO! Se detectó OpenHardwareMonitor instalado en el sistema.${NC}"
        echo -e "${YELLOW}   Esto NO es parte de SysMonitorPro, pero se recomendó durante la instalación.${NC}"
        read -p "¿Deseas eliminar OpenHardwareMonitor del sistema? (s/N): " -r eliminar_ohm
        if [[ $eliminar_ohm =~ ^[Ss]$ ]]; then
            echo -e "${RED}   Eliminando OpenHardwareMonitor...${NC}"
            "C:/Program Files/OpenHardwareMonitor/Uninstall.exe" /S 2>/dev/null || rm -rf "C:/Program Files/OpenHardwareMonitor"
            echo -e "${GREEN}✓ OpenHardwareMonitor eliminado.${NC}"
        else
            echo -e "${D}➜ OpenHardwareMonitor conservado.${NC}"
        fi
    fi
fi

# === 8. ELIMINAR PYTHON O PIP (SOLO SI EL USUARIO LO PIDE EXPLÍCITAMENTE) ===
echo ""
echo -e "${RED}${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${RED}${BOLD}⚠️  SECCIÓN PELIGROSA: Modificación del sistema ⚠️${NC}"
echo -e "${RED}${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}⚠️  ¡ATENCIÓN! Estos componentes son necesarios para otros programas.${NC}"
echo -e "${YELLOW}⚠️  Si no estás seguro de su uso, elige 'NO'.${NC}"

# --- 8a. Eliminar pip (solo si el usuario lo confirma) ---
if command -v pip3 &> /dev/null; then
    echo ""
    read -p "¿Eliminar pip3 del sistema? (s/N): " -r eliminar_pip_sistema
    if [[ $eliminar_pip_sistema =~ ^[Ss]$ ]]; then
        echo -e "${RED}   Eliminando pip3...${NC}"
        sudo apt remove -y python3-pip 2>/dev/null || sudo dnf remove -y python3-pip 2>/dev/null || sudo pacman -R python-pip 2>/dev/null
        echo -e "${GREEN}✓ pip3 eliminado del sistema.${NC}"
    else
        echo -e "${D}➜ pip3 conservado.${NC}"
    fi
fi

# --- 8b. Eliminar Python (¡Último recurso! Aviso muy fuerte) ---
if command -v python3 &> /dev/null; then
    echo ""
    echo -e "${RED}${BOLD}════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}${BOLD}⚠️  ¡ELIMINAR PYTHON PUEDE ROMPER MUCHOS PROGRAMAS! ⚠️${NC}"
    echo -e "${RED}${BOLD}════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Python lo usan el sistema operativo y muchas aplicaciones.${NC}"
    echo -e "${YELLOW}Eliminarlo puede dejar inoperativo tu sistema.${NC}"
    read -p "¿ESTÁS COMPLETAMENTE SEGURO DE ELIMINAR PYTHON3? (escribe 'ELIMINAR' para confirmar): " confirmacion
    if [[ "$confirmacion" == "ELIMINAR" ]]; then
        echo -e "${RED}   Eliminando Python3...${NC}"
        sudo apt remove -y python3 python3-venv 2>/dev/null || sudo dnf remove -y python3 2>/dev/null || sudo pacman -R python 2>/dev/null
        echo -e "${GREEN}✓ Python3 eliminado del sistema.${NC}"
        echo -e "${RED}⚠️  Se recomienda reinstalar el sistema si dejó de funcionar correctamente.${NC}"
    else
        echo -e "${D}➜ Python conservado.${NC}"
    fi
fi

# === 9. ELIMINAR LA CARPETA DEL PROGRAMA (OPCIONAL - NUEVO) ===
echo ""
echo -e "${YELLOW}🔍 ¿Deseas eliminar también la carpeta completa del repositorio?${NC}"
echo -e "${YELLOW}   (Ubicación actual: ${BOLD}$(pwd)${NC}${YELLOW})${NC}"
read -p "¿Eliminar TODA esta carpeta? (s/N): " -r eliminar_repo
if [[ $eliminar_repo =~ ^[Ss]$ ]]; then
    cd ..
    echo -e "${RED}   Eliminando repositorio...${NC}"
    rm -rf "$(pwd)/Sysmonitorpro" 2>/dev/null || rm -rf "$(dirname "$0")" 2>/dev/null
    echo -e "${GREEN}✓ Repositorio eliminado.${NC}"
    echo -e "${YELLOW}⚠️  La terminal se cerrará en 5 segundos...${NC}"
    sleep 5
    exit 0
else
    echo -e "${D}➜ Repositorio conservado.${NC}"
fi

# === 10. FINAL ===
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Desinstalación completada. Sistema limpio.${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
