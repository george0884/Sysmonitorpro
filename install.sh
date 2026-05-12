#!/bin/bash
# install.sh - Instalador completo de SysMonitorPro
# Compatible con Python 3.14+

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   SysMonitorPro - Instalador Automático${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# ===== 1. DETECTAR VERSIÓN DE PYTHON =====
echo -e "\n${YELLOW}▶ Detectando Python...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} detectado${NC}"

# ===== 2. INSTALAR EL PAQUETE VENV CORRECTO =====
echo -e "\n${YELLOW}▶ Instalando python${PYTHON_MAJOR}.${PYTHON_MINOR}-venv...${NC}"

# Intentar instalar la versión específica
if ! sudo apt install -y python${PYTHON_MAJOR}.${PYTHON_MINOR}-venv 2>/dev/null; then
    echo -e "${YELLOW}⚠ Versión específica no encontrada, instalando python3-venv...${NC}"
    sudo apt install -y python3-venv python3-full
fi

# Verificar que venv funciona
echo -e "\n${YELLOW}▶ Probando módulo venv...${NC}"
if ! python3 -c "import venv" 2>/dev/null; then
    echo -e "${RED}✗ Error: módulo venv no disponible${NC}"
    echo -e "${YELLOW}Instalación manual requerida:${NC}"
    echo "  sudo apt install python3.14-venv"
    echo "  O actualiza tu sistema: sudo apt update && sudo apt upgrade"
    exit 1
fi
echo -e "${GREEN}✓ Módulo venv disponible${NC}"

# ===== 3. CREAR ENTORNO VIRTUAL =====
echo -e "\n${YELLOW}▶ Creando entorno virtual...${NC}"

# Eliminar entorno corrupto si existe
if [ -d "venv" ]; then
    echo -e "${YELLOW}Eliminando entorno existente...${NC}"
    rm -rf venv
fi

# Crear entorno virtual (con pip incluido)
echo -e "${YELLOW}Creando nuevo entorno...${NC}"
python3 -m venv venv --without-pip 2>/dev/null || python3 -m venv venv

# Si no tiene pip, instalarlo manualmente
if [ ! -f "venv/bin/pip" ]; then
    echo -e "${YELLOW}Instalando pip manualmente...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    venv/bin/python get-pip.py
    rm get-pip.py
fi

# Verificar
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}✗ Error crítico: No se pudo crear el entorno virtual${NC}"
    echo -e "${YELLOW}Solución alternativa (sin entorno virtual):${NC}"
    echo "  pip3 install --user psutil"
    echo "  python3 sysmonitorpro.py"
    exit 1
fi

echo -e "${GREEN}✓ Entorno virtual creado exitosamente${NC}"

# ===== 4. ACTIVAR E INSTALAR =====
echo -e "\n${YELLOW}▶ Instalando psutil...${NC}"
source venv/bin/activate

# Instalar psutil
pip install --upgrade pip 2>/dev/null || true
pip install psutil

echo -e "${GREEN}✓ psutil instalado correctamente${NC}"

# ===== 5. PREGUNTAR POR SOPORTE GPU (NUEVO) =====
echo -e "\n${YELLOW}▶ ¿Instalar soporte para GPU? (s/n)${NC}"
read -r instalar_gpu
if [[ $instalar_gpu == "s" || $instalar_gpu == "S" ]]; then
    echo -e "${YELLOW}Instalando GPUtil...${NC}"
    pip install gputil
    echo -e "${YELLOW}Instalando pyamdgpuinfo para AMD...${NC}"
    pip install pyamdgpuinfo
    echo -e "${GREEN}✓ Soporte GPU instalado${NC}"
fi

# ===== 6. CREAR CONFIGURACIÓN =====
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

# ===== 7. CREAR LANZADOR =====
cat > sysmonitor << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 sysmonitorpro.py "$@"
EOF
chmod +x sysmonitor
echo -e "${GREEN}✓ Lanzador creado: ./sysmonitor${NC}"

# ===== 8. PREGUNTAR POR COMANDO GLOBAL (NUEVO) =====
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
        echo -e "${GREEN}✓ Ahora puedes ejecutar 'sysmonitor' desde cualquier lugar${NC}"
    fi
fi

# ===== 9. PRUEBA =====
echo -e "\n${YELLOW}▶ Probando instalación...${NC}"
if source venv/bin/activate && python3 -c "import psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ Todo funciona correctamente${NC}"
else
    echo -e "${RED}✗ Error en la prueba${NC}"
fi

# ===== 10. LIMPIEZA FINAL (AUTOREMOVE) =====
echo -e "\n${YELLOW}▶ Limpiando archivos temporales y no esenciales...${NC}"

# Archivos que definitivamente se pueden eliminar
echo -e "${YELLOW}Eliminando archivos de documentación e imágenes...${NC}"
rm -f *.png *.jpg *.jpeg *.gif *.bmp 2>/dev/null || true
rm -f powershell.jpg Linux.png 1.png 2.png 2>&1 >/dev/null

# Archivos de configuración de ejemplo (ya se copió la configuración real)
echo -e "${YELLOW}Eliminando ejemplos de configuración...${NC}"
rm -f config/example.json 2>/dev/null || true

# Archivos de dependencias (el entorno virtual ya tiene lo necesario)
echo -e "${YELLOW}Eliminando archivos de requisitos...${NC}"
rm -f requeriments-*.txt requirements-*.txt 2>/dev/null || true

# Scripts auxiliares de Windows (no necesarios en Linux)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "cygwin" && "$OSTYPE" != "win32" ]]; then
    echo -e "${YELLOW}Eliminando scripts específicos de Windows...${NC}"
    rm -f *.bat *.ps1 2>/dev/null || true
fi

# Archivos de construcción obsoletos
echo -e "${YELLOW}Eliminando archivos de construcción...${NC}"
rm -rf build/ dist/ *.spec 2>/dev/null || true
rm -f *.AppImage 2>/dev/null || true
rm -f appimagetool-*.AppImage 2>/dev/null || true
rm -f linuxdeploy-*.AppImage 2>/dev/null || true
rm -f create-appimage.sh build-appimage.sh simple-build.sh 2>/dev/null || true

echo -e "${GREEN}✓ Limpieza completada${NC}"
echo -e "\n${GREEN}NOTA: Los archivos esenciales (sysmonitorpro.py, venv/, config/, install.sh, LICENSE, README.md) se han conservado.${NC}"

# ===== 11. FINAL =====
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
