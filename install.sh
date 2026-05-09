#!/bin/bash
# install.sh - Instalador completo de SysMonitorPro

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   SysMonitorPro - Instalador Automático${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# 1. Verificar Python
echo -e "\n${YELLOW}▶ Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 no instalado. Instalando...${NC}"
    sudo apt update && sudo apt install -y python3 python3-pip
else
    echo -e "${GREEN}✓ Python3 encontrado: $(python3 --version)${NC}"
fi

# 2. Verificar pip
echo -e "\n${YELLOW}▶ Verificando pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}✗ pip3 no instalado. Instalando...${NC}"
    sudo apt install -y python3-pip
else
    echo -e "${GREEN}✓ pip3 encontrado${NC}"
fi

# 3. Instalar dependencias Python
echo -e "\n${YELLOW}▶ Instalando dependencias Python...${NC}"
pip3 install --user psutil
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ psutil instalado correctamente${NC}"
else
    echo -e "${RED}✗ Error instalando psutil${NC}"
    exit 1
fi

# 4. Instalar dependencias opcionales para GPU
echo -e "\n${YELLOW}▶ ¿Instalar soporte para GPU? (s/n)${NC}"
read -r instalar_gpu
if [[ $instalar_gpu == "s" || $instalar_gpu == "S" ]]; then
    echo -e "${YELLOW}Instalando GPUtil...${NC}"
    pip3 install --user gputil
    echo -e "${YELLOW}Instalando pyamdgpuinfo...${NC}"
    pip3 install --user pyamdgpuinfo
    echo -e "${GREEN}✓ Soporte GPU instalado${NC}"
fi

# 5. Crear directorio de configuración
echo -e "\n${YELLOW}▶ Configurando archivos del usuario...${NC}"
CONFIG_DIR="$HOME/.config/sysmonitorpro"
mkdir -p "$CONFIG_DIR"

# Crear configuración por defecto si no existe
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

# 6. Instalar script globalmente (opcional)
echo -e "\n${YELLOW}▶ ¿Instalar comando global 'sysmonitor'? (s/n)${NC}"
read -r instalar_global
if [[ $instalar_global == "s" || $instalar_global == "S" ]]; then
    # Obtener ruta del script actual
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Crear alias/script en /usr/local/bin
    sudo tee /usr/local/bin/sysmonitor > /dev/null << EOF
#!/bin/bash
python3 "$SCRIPT_DIR/sysmonitorpro.py" "\$@"
EOF
    sudo chmod +x /usr/local/bin/sysmonitor
    echo -e "${GREEN}✓ Comando 'sysmonitor' disponible en todo el sistema${NC}"
fi

# 7. Verificar GPU detectada
echo -e "\n${YELLOW}▶ Detectando hardware...${NC}"
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA GPU detectada${NC}"
elif command -v rocm-smi &> /dev/null; then
    echo -e "${GREEN}✓ AMD GPU detectada (ROCm)${NC}"
else
    echo -e "${YELLOW}⚠ No se detectó GPU dedicada o drivers no instalados${NC}"
fi

# 8. Mostrar temperatura CPU (verificar sensores)
if command -v sensors &> /dev/null; then
    echo -e "${GREEN}✓ lm-sensors detectado (temperaturas disponibles)${NC}"
else
    echo -e "${YELLOW}⚠ lm-sensors no instalado. Para temperaturas CPU:${NC}"
    echo -e "  sudo apt install lm-sensors && sudo sensors-detect"
fi

# 9. Finalizar
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Instalación completada con éxito!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Para ejecutar:${NC}"
echo -e "  python3 sysmonitorpro.py"
echo -e "  O si instalaste global: sysmonitor"
echo -e "\n${YELLOW}Para ver opciones avanzadas:${NC}"
echo -e "  sysmonitor --help"
echo -e "\n${YELLOW}Configuración personalizada:${NC}"
echo -e "  nano ~/.config/sysmonitorpro/config.json"
echo -e "\n${GREEN}¡Disfruta de SysMonitorPro! 🚀${NC}"
