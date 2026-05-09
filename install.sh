#!/bin/bash
# install.sh - Instalador completo de SysMonitorPro
# Compatible con Python 3.14+ (externally-managed-environment)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   SysMonitorPro - Instalador Automático${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Verificar Python
echo -e "\n${YELLOW}▶ Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 no instalado. Instalando...${NC}"
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
else
    echo -e "${GREEN}✓ Python3 encontrado: $(python3 --version)${NC}"
fi

# ===== NUEVA SECCIÓN PARA PYTHON 3.14+ =====
echo -e "\n${YELLOW}▶ Configurando entorno virtual...${NC}"

# Verificar si existe entorno virtual
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creando entorno virtual...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Entorno virtual creado${NC}"
else
    echo -e "${GREEN}✓ Entorno virtual ya existe${NC}"
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar psutil en el entorno virtual
echo -e "\n${YELLOW}▶ Instalando dependencias en entorno virtual...${NC}"
pip install psutil
echo -e "${GREEN}✓ psutil instalado correctamente${NC}"

# Crear directorio de configuración
echo -e "\n${YELLOW}▶ Configurando archivos del usuario...${NC}"
CONFIG_DIR="$HOME/.config/sysmonitorpro"
mkdir -p "$CONFIG_DIR"

# Crear configuración por defecto
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
    echo -e "${GREEN}✓ Configuración creada en $CONFIG_DIR/config.json${NC}"
else
    echo -e "${GREEN}✓ Configuración ya existe${NC}"
fi

# Crear script de lanzamiento (que activa el entorno virtual automáticamente)
echo -e "\n${YELLOW}▶ Creando lanzador...${NC}"
cat > sysmonitor << EOF
#!/bin/bash
cd $(pwd)
source venv/bin/activate
python3 sysmonitorpro.py "\$@"
EOF
chmod +x sysmonitor
echo -e "${GREEN}✓ Lanzador creado: ./sysmonitor${NC}"

# Finalizar
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Instalación completada con éxito!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Para ejecutar:${NC}"
echo -e "  ./sysmonitor"
echo -e "  O activa el entorno manual: source venv/bin/activate && python3 sysmonitorpro.py"
echo -e "\n${YELLOW}Configuración personalizada:${NC}"
echo -e "  nano ~/.config/sysmonitorpro/config.json"
echo -e "\n${GREEN}¡Disfruta de SysMonitorPro! 🚀${NC}"
