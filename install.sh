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

# ===== 5. CREAR CONFIGURACIÓN =====
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

# ===== 6. CREAR LANZADOR =====
cat > sysmonitor << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 sysmonitorpro.py "$@"
EOF
chmod +x sysmonitor
echo -e "${GREEN}✓ Lanzador creado: ./sysmonitor${NC}"

# ===== 7. PRUEBA =====
echo -e "\n${YELLOW}▶ Probando instalación...${NC}"
if source venv/bin/activate && python3 -c "import psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ Todo funciona correctamente${NC}"
else
    echo -e "${RED}✗ Error en la prueba${NC}"
fi

# ===== 8. FINAL =====
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Instalación completada!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Para ejecutar:${NC}"
echo -e "  ./sysmonitor"
echo -e "\n${GREEN}¡Disfruta de SysMonitorPro! 🚀${NC}"
