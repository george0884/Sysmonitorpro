#!/bin/bash
# install.sh - Instalador completo de SysMonitorPro
# Compatible con Python 3.14+

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   SysMonitorPro - Instalador Automático${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# ===== 1. DETECTAR SISTEMA OPERATIVO =====
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    IS_LINUX=true
    IS_WINDOWS=false
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    IS_LINUX=false
    IS_WINDOWS=true
else
    IS_LINUX=false
    IS_WINDOWS=false
fi

# ===== 2. DETECTAR VERSIÓN DE PYTHON =====
echo -e "\n${YELLOW}▶ Detectando Python...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} detectado${NC}"

# ===== 3. INSTALAR VENV (si es Linux) =====
if [ "$IS_LINUX" = true ]; then
    echo -e "\n${YELLOW}▶ Instalando python${PYTHON_MAJOR}.${PYTHON_MINOR}-venv...${NC}"
    if ! sudo apt install -y python${PYTHON_MAJOR}.${PYTHON_MINOR}-venv 2>/dev/null; then
        echo -e "${YELLOW}⚠ Versión específica no encontrada, instalando python3-venv...${NC}"
        sudo apt install -y python3-venv python3-full
    fi
fi

# ===== 4. VERIFICAR MÓDULO VENV =====
echo -e "\n${YELLOW}▶ Probando módulo venv...${NC}"
if ! python3 -c "import venv" 2>/dev/null; then
    echo -e "${RED}✗ Error: módulo venv no disponible${NC}"
    echo -e "${YELLOW}Solución: sudo apt install python3-venv${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Módulo venv disponible${NC}"

# ===== 5. CREAR ENTORNO VIRTUAL =====
echo -e "\n${YELLOW}▶ Creando entorno virtual...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}Eliminando entorno existente...${NC}"
    rm -rf venv
fi
python3 -m venv venv --without-pip 2>/dev/null || python3 -m venv venv

# Instalar pip manualmente si falta
if [ ! -f "venv/bin/pip" ]; then
    echo -e "${YELLOW}Instalando pip manualmente...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    venv/bin/python get-pip.py
    rm get-pip.py
fi

if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}✗ Error crítico: No se pudo crear el entorno virtual${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Entorno virtual creado exitosamente${NC}"

# ===== 6. ACTIVAR Y INSTALAR PSUTIL =====
echo -e "\n${YELLOW}▶ Instalando psutil...${NC}"
source venv/bin/activate
pip install --upgrade pip 2>/dev/null || true
pip install psutil
echo -e "${GREEN}✓ psutil instalado correctamente${NC}"

# ===== 7. SOPORTE GPU OPCIONAL =====
echo -e "\n${YELLOW}▶ ¿Instalar soporte para GPU? (s/n)${NC}"
read -r instalar_gpu
if [[ $instalar_gpu == "s" || $instalar_gpu == "S" ]]; then
    echo -e "${YELLOW}Instalando GPUtil...${NC}"
    pip install gputil
    if [ "$IS_LINUX" = true ]; then
        echo -e "${YELLOW}Instalando pyamdgpuinfo para AMD...${NC}"
        pip install pyamdgpuinfo
    fi
    echo -e "${GREEN}✓ Soporte GPU instalado${NC}"
fi

# ===== 8. CREAR CONFIGURACIÓN =====
echo -e "\n${YELLOW}▶ Configurando archivos...${NC}"
CONFIG_DIR="$HOME/.config/sysmonitorpro"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
    "intervalo": 1.0,
    "mostrar_gpu": true,
    "mostrar_discos": true,
    "mostrar_red": true,
    "mostrar_top": true,
    "grafico_tamano": 40,
    "historial_segundos": 60,
    "interfaz_red": "auto"
}
EOF
    echo -e "${GREEN}✓ Configuración creada${NC}"
fi

# ===== 9. CREAR LANZADOR LOCAL =====
cat > sysmonitor << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 sysmonitorpro.py "$@"
EOF
chmod +x sysmonitor
echo -e "${GREEN}✓ Lanzador creado: ./sysmonitor${NC}"

# ===== 10. INSTALAR COMANDO GLOBAL =====
echo -e "\n${YELLOW}▶ ¿Instalar comando global 'sysmonitor'? (s/n)${NC}"
read -r instalar_global
if [[ $instalar_global == "s" || $instalar_global == "S" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SCRIPT_PATH="$SCRIPT_DIR/sysmonitorpro.py"
    if [ ! -f "$SCRIPT_PATH" ]; then
        echo -e "${RED}✗ Error: No se encuentra sysmonitorpro.py${NC}"
    else
        sudo tee /usr/local/bin/sysmonitor > /dev/null << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 "$SCRIPT_PATH" "\$@"
EOF
        sudo chmod +x /usr/local/bin/sysmonitor
        echo -e "${GREEN}✓ Comando 'sysmonitor' instalado en /usr/local/bin/${NC}"
    fi
fi

# ===== 11. PRUEBA RÁPIDA =====
echo -e "\n${YELLOW}▶ Probando instalación...${NC}"
if source venv/bin/activate && python3 -c "import psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ Todo funciona correctamente${NC}"
else
    echo -e "${RED}✗ Error en la prueba${NC}"
fi

# ===== 12. LIMPIEZA DE ARCHIVOS ESPECÍFICOS DE WINDOWS (SOLO EN LINUX) =====
if [ "$IS_LINUX" = true ]; then
    echo -e "\n${YELLOW}▶ Detectado sistema Linux. Eliminando archivos innecesarios para Windows...${NC}"
    
    # Scripts de Windows
    echo -e "${YELLOW}   Eliminando scripts de Windows (.bat, .ps1)...${NC}"
    rm -f *.bat 2>/dev/null || true
    rm -f install-python-windows.bat 2>/dev/null || true
    rm -f *.ps1 2>/dev/null || true
    
    # Archivos de requisitos de Windows
    echo -e "${YELLOW}   Eliminando archivos de requisitos para Windows...${NC}"
    rm -f requeriments-windows.txt 2>/dev/null || true
    rm -f requirements-windows.txt 2>/dev/null || true
    
    # Imágenes de documentación de Windows
    echo -e "${YELLOW}   Eliminando imágenes de documentación de Windows...${NC}"
    rm -f powershell.jpg 2>/dev/null || true
    rm -f Windows*.png 2>/dev/null || true
    rm -f *.jpg 2>/dev/null || true
    
    # Archivos de construcción obsoletos (AppImage, etc.)
    echo -e "${YELLOW}   Eliminando residuos de compilación...${NC}"
    rm -rf build/ dist/ *.spec 2>/dev/null || true
    rm -f *.AppImage 2>/dev/null || true
    rm -f appimagetool-*.AppImage 2>/dev/null || true
    rm -f linuxdeploy-*.AppImage 2>/dev/null || true
    rm -f create-appimage.sh build-appimage.sh simple-build.sh 2>/dev/null || true
    
    # Ejemplos de configuración
    echo -e "${YELLOW}   Eliminando ejemplos de configuración...${NC}"
    rm -f config/example.json 2>/dev/null || true
    
    echo -e "${GREEN}✓ Archivos específicos de Windows eliminados.${NC}"
    echo -e "${GREEN}✓ Residuos de compilación eliminados.${NC}"
fi

# ===== 13. FINAL =====
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Instalación completada!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Para ejecutar:${NC}"
echo -e "  ./sysmonitor                # Desde la carpeta del proyecto"
if [[ $instalar_global == "s" || $instalar_global == "S" ]]; then
    echo -e "  sysmonitor                  # Desde cualquier lugar"
fi
echo -e "\n${YELLOW}Para ver opciones:${NC}"
echo -e "  sysmonitor --help"
echo -e "\n${GREEN}¡Disfruta de SysMonitorPro! 🚀${NC}"
