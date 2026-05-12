#!/bin/bash
# uninstall.sh - Desinstalador interactivo seguro para SysMonitorPro
# Funciona desde CUALQUIER directorio donde se ejecute

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'
D='\033[2m'

# === DETECTAR LA CARPETA DONDE ESTÁ EL SCRIPT ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${RED}   SysMonitorPro - Desinstalador Interactivo${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠️  ATENCIÓN: Este script eliminará componentes de SysMonitorPro.${NC}"
echo -e "${YELLOW}⚠️  Te preguntaremos ANTES de eliminar cada cosa.${NC}"
echo ""
echo -e "${D}📁 Carpeta detectada: ${SCRIPT_DIR}${NC}"
echo ""
read -p "¿Deseas continuar con la desinstalación? (s/N): " -r continuar
if [[ ! $continuar =~ ^[Ss]$ ]]; then
    echo -e "${GREEN}Operación cancelada. No se eliminó nada.${NC}"
    exit 0
fi

# === 1. ELIMINAR COMANDO GLOBAL ===
if command -v sysmonitor &> /dev/null; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó el comando global 'sysmonitor'${NC}"
    read -p "¿Deseas eliminar este comando global? (s/N): " -r eliminar_comando
    if [[ $eliminar_comando =~ ^[Ss]$ ]]; then
        sudo rm -f /usr/local/bin/sysmonitor 2>/dev/null
        echo -e "${GREEN}✓ Comando global eliminado.${NC}"
    else
        echo -e "${D}➜ Comando global conservado.${NC}"
    fi
else
    echo -e "${D}➜ No se encontró el comando global.${NC}"
fi

# === 2. ELIMINAR LANZADOR LOCAL ===
if [ -f "$SCRIPT_DIR/sysmonitor" ]; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó el lanzador local './sysmonitor'${NC}"
    read -p "¿Deseas eliminar este lanzador local? (s/N): " -r eliminar_lanzador
    if [[ $eliminar_lanzador =~ ^[Ss]$ ]]; then
        rm -f "$SCRIPT_DIR/sysmonitor" 2>/dev/null
        echo -e "${GREEN}✓ Lanzador local eliminado.${NC}"
    else
        echo -e "${D}➜ Lanzador local conservado.${NC}"
    fi
fi

# === 3. ELIMINAR ENTORNO VIRTUAL ===
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó el entorno virtual 'venv'${NC}"
    read -p "¿Deseas eliminar este entorno virtual? (s/N): " -r eliminar_venv
    if [[ $eliminar_venv =~ ^[Ss]$ ]]; then
        rm -rf "$SCRIPT_DIR/venv" 2>/dev/null
        echo -e "${GREEN}✓ Entorno virtual eliminado.${NC}"
    else
        echo -e "${D}➜ Entorno virtual conservado.${NC}"
    fi
fi

# === 4. ELIMINAR CONFIGURACIÓN DEL USUARIO ===
CONFIG_DIR="$HOME/.config/sysmonitorpro"
if [ -d "$CONFIG_DIR" ]; then
    echo ""
    echo -e "${YELLOW}🔍 Se detectó configuración en: $CONFIG_DIR${NC}"
    read -p "¿Deseas eliminar la configuración? (s/N): " -r eliminar_config
    if [[ $eliminar_config =~ ^[Ss]$ ]]; then
        rm -rf "$CONFIG_DIR" 2>/dev/null
        echo -e "${GREEN}✓ Configuración eliminada.${NC}"
    else
        echo -e "${D}➜ Configuración conservada.${NC}"
    fi
fi

# === 5. ELIMINAR DEPENDENCIAS PYTHON ===
echo ""
echo -e "${YELLOW}🔍 Buscando paquetes de Python...${NC}"
PAQUETES=("psutil" "gputil" "pyamdgpuinfo")
PAQUETES_A_ELIMINAR=()

for paquete in "${PAQUETES[@]}"; do
    if pip3 show "$paquete" &> /dev/null 2>&1; then
        echo -e "   - $paquete"
        PAQUETES_A_ELIMINAR+=("$paquete")
    fi
done

if [ ${#PAQUETES_A_ELIMINAR[@]} -gt 0 ]; then
    echo ""
    read -p "¿Deseas desinstalar estos paquetes? (s/N): " -r eliminar_pip
    if [[ $eliminar_pip =~ ^[Ss]$ ]]; then
        for paquete in "${PAQUETES_A_ELIMINAR[@]}"; do
            echo -e "${YELLOW}   Desinstalando $paquete...${NC}"
            pip3 uninstall -y "$paquete" 2>/dev/null || true
        done
        echo -e "${GREEN}✓ Paquetes eliminados.${NC}"
    else
        echo -e "${D}➜ Paquetes conservados.${NC}"
    fi
else
    echo -e "${D}➜ No se encontraron paquetes.${NC}"
fi

# === 6. ELIMINAR RESIDUOS DE COMPILACIÓN ===
if [ -d "$SCRIPT_DIR/build" ] || [ -d "$SCRIPT_DIR/dist" ] || ls "$SCRIPT_DIR"/*.spec &> /dev/null 2>&1; then
    echo ""
    read -p "¿Deseas eliminar residuos de compilación (build, dist, *.spec)? (s/N): " -r eliminar_residuos
    if [[ $eliminar_residuos =~ ^[Ss]$ ]]; then
        rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist" "$SCRIPT_DIR"/*.spec "$SCRIPT_DIR"/*.AppImage 2>/dev/null
        echo -e "${GREEN}✓ Residuos eliminados.${NC}"
    else
        echo -e "${D}➜ Residuos conservados.${NC}"
    fi
fi

# === 7. ELIMINAR PYTHON (SOLO SI EL USUARIO INSISTE) ===
echo ""
echo -e "${RED}${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${RED}${BOLD}⚠️  SECCIÓN PELIGROSA: Modificación del sistema ⚠️${NC}"
echo -e "${RED}${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}⚠️  ¡ATENCIÓN! Estos componentes son necesarios para otros programas.${NC}"
echo -e "${YELLOW}⚠️  Si no estás seguro de su uso, elige 'NO'.${NC}"

read -p "¿Eliminar pip3 del sistema? (s/N): " -r eliminar_pip_sistema
if [[ $eliminar_pip_sistema =~ ^[Ss]$ ]]; then
    echo -e "${RED}   Eliminando pip3...${NC}"
    sudo apt remove -y python3-pip 2>/dev/null || sudo dnf remove -y python3-pip 2>/dev/null || sudo pacman -R python-pip 2>/dev/null
    echo -e "${GREEN}✓ pip3 eliminado.${NC}"
fi

echo ""
echo -e "${RED}⚠️  ELIMINAR PYTHON PUEDE ROMPER EL SISTEMA ⚠️${NC}"
read -p "¿ESCRIBE 'ELIMINAR' para confirmar la eliminación de Python3? " confirmacion
if [[ "$confirmacion" == "ELIMINAR" ]]; then
    echo -e "${RED}   Eliminando Python3...${NC}"
    sudo apt remove -y python3 python3-venv 2>/dev/null || sudo dnf remove -y python3 2>/dev/null || sudo pacman -R python 2>/dev/null
    echo -e "${GREEN}✓ Python3 eliminado.${NC}"
    echo -e "${RED}⚠️  Se recomienda reinstalar el sistema si dejó de funcionar correctamente.${NC}"
else
    echo -e "${D}➜ Python conservado.${NC}"
fi

# === 8. ELIMINAR LA CARPETA DEL PROGRAMA (FUNCIONA DESDE CUALQUIER DIRECTORIO) ===
echo ""
echo -e "${YELLOW}🔍 ¿Deseas eliminar también la carpeta completa del repositorio?${NC}"
echo -e "${YELLOW}   (Ubicación: ${BOLD}${SCRIPT_DIR}${NC}${YELLOW})${NC}"
read -p "¿Eliminar TODA esta carpeta? (s/N): " -r eliminar_repo
if [[ $eliminar_repo =~ ^[Ss]$ ]]; then
    CARPETA_A_ELIMINAR="$SCRIPT_DIR"
    cd /tmp
    echo -e "${RED}   Eliminando: $CARPETA_A_ELIMINAR${NC}"
    rm -rf "$CARPETA_A_ELIMINAR"
    echo -e "${GREEN}✓ Repositorio eliminado.${NC}"
    echo -e "${YELLOW}⚠️  La terminal se cerrará en 5 segundos...${NC}"
    sleep 5
    exit 0
else
    echo -e "${D}➜ Repositorio conservado.${NC}"
fi

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Desinstalación completada.${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
