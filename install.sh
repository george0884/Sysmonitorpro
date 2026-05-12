#!/bin/bash
# install.sh - Instalador interactivo para SysMonitorPro (Linux)
# Compatible con Python 3.8+

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'
D='\033[2m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   SysMonitorPro - Instalador Interactivo (Linux)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# === DETECTAR CARPETA DEL SCRIPT ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${D}📁 Carpeta del proyecto: ${SCRIPT_DIR}${NC}"
echo ""

# === 1. DETECTAR PYTHON ===
echo -e "${YELLOW}▶ Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 no instalado.${NC}"
    echo -e "${YELLOW}  Instalando...${NC}"
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
else
    echo -e "${GREEN}✓ Python3 encontrado: $(python3 --version)${NC}"
fi

# Obtener versión de Python
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${D}  Versión detectada: Python ${PYTHON_VERSION}${NC}"

# === 2. VERIFICAR/INSTALAR VENV (SOLUCIÓN PARA PYTHON 3.14+) ===
echo -e "\n${YELLOW}▶ Verificando módulo venv...${NC}"

# Probar si venv funciona
if ! python3 -c "import venv" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Módulo venv no disponible. Instalando...${NC}"
    
    # Intentar instalar la versión específica de Python
    if ! sudo apt install -y python${PYTHON_VERSION}-venv 2>/dev/null; then
        echo -e "${YELLOW}  Versión específica no encontrada, intentando python3-venv...${NC}"
        sudo apt install -y python3-venv
    fi
    
    # Si aún falla, instalar python3-full (para Ubuntu 24.04+)
    if ! python3 -c "import venv" 2>/dev/null; then
        echo -e "${YELLOW}  Instalando python3-full...${NC}"
        sudo apt install -y python3-full
    fi
    
    # Verificar que se instaló correctamente
    if ! python3 -c "import venv" 2>/dev/null; then
        echo -e "${RED}✗ Error: No se pudo instalar el módulo venv${NC}"
        echo -e "${YELLOW}  Solución manual:${NC}"
        echo "    sudo apt install python${PYTHON_VERSION}-venv"
        echo "    O ejecuta: sudo apt install python3-venv"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Módulo venv disponible${NC}"

# === 3. VERIFICAR/INSTALAR PIP ===
echo -e "\n${YELLOW}▶ Verificando pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}  Instalando pip...${NC}"
    sudo apt install -y python3-pip
fi
echo -e "${GREEN}✓ pip3 disponible${NC}"

# === 4. CREAR ENTORNO VIRTUAL ===
echo -e "\n${YELLOW}▶ Creando entorno virtual...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}  Eliminando entorno existente...${NC}"
    rm -rf venv
fi

# Crear entorno virtual con manejo de errores
if ! python3 -m venv venv 2>/dev/null; then
    echo -e "${YELLOW}  Error al crear venv. Intentando con virtualenv...${NC}"
    pip3 install --user virtualenv
    ~/.local/bin/virtualenv venv
    
    if [ ! -f "venv/bin/activate" ]; then
        echo -e "${RED}✗ Error: No se pudo crear el entorno virtual${NC}"
        echo -e "${YELLOW}  Solución alternativa: instalar manualmente${NC}"
        echo "    sudo apt install python3-venv"
        echo "    sudo apt install python3-full"
        exit 1
    fi
fi

if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}✗ Error: No se pudo crear el entorno virtual${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Entorno virtual creado${NC}"

# === 5. ACTIVAR E INSTALAR PSUTIL ===
echo -e "\n${YELLOW}▶ Instalando dependencias...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install psutil

if python3 -c "import psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ psutil instalado correctamente${NC}"
else
    echo -e "${RED}✗ Error: psutil no se instaló correctamente${NC}"
    exit 1
fi

# === 6. SOPORTE GPU OPCIONAL ===
echo -e "\n${YELLOW}▶ ¿Instalar soporte para GPU? (s/n)${NC}"
read -r instalar_gpu
if [[ $instalar_gpu == "s" || $instalar_gpu == "S" ]]; then
    echo -e "${YELLOW}  Instalando GPUtil...${NC}"
    pip install gputil
    echo -e "${YELLOW}  Instalando pyamdgpuinfo...${NC}"
    pip install pyamdgpuinfo
    echo -e "${GREEN}✓ Soporte GPU instalado${NC}"
fi

# === 7. CREAR CONFIGURACIÓN ===
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
    echo -e "${GREEN}✓ Configuración creada en $CONFIG_DIR/config.json${NC}"
else
    echo -e "${D}✓ Configuración ya existe${NC}"
fi

# === 8. CREAR LANZADOR LOCAL ===
echo -e "\n${YELLOW}▶ Creando lanzador local...${NC}"
cat > sysmonitor << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 sysmonitorpro.py "$@"
EOF
chmod +x sysmonitor
echo -e "${GREEN}✓ Lanzador creado: ./sysmonitor${NC}"

# === 9. COMANDO GLOBAL OPCIONAL ===
echo -e "\n${YELLOW}▶ ¿Instalar comando global 'sysmonitor'? (s/n)${NC}"
read -r instalar_global
if [[ $instalar_global == "s" || $instalar_global == "S" ]]; then
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

# === 10. CREAR ICONO ===
echo -e "\n${YELLOW}▶ Creando icono...${NC}"
if [ ! -f "$SCRIPT_DIR/icon.png" ]; then
    # Crear icono SVG y convertirlo a PNG
    cat > /tmp/icon.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <circle cx="128" cy="128" r="110" fill="#1a1a2e" stroke="#7c7cff" stroke-width="8"/>
  <text x="128" y="170" font-family="monospace" font-size="90" font-weight="bold" fill="#7c7cff" text-anchor="middle">S</text>
  <text x="128" y="220" font-family="monospace" font-size="25" font-weight="bold" fill="#7c7cff" text-anchor="middle">M</text>
  <text x="128" y="242" font-family="monospace" font-size="12" fill="#7c7cff" text-anchor="middle">Pro</text>
</svg>
EOF
    # Intentar convertir SVG a PNG (si ImageMagick está instalado)
    if command -v convert &> /dev/null; then
        convert /tmp/icon.svg -resize 256x256 "$SCRIPT_DIR/icon.png"
        echo -e "${GREEN}✓ Icono PNG creado${NC}"
    else
        echo -e "${YELLOW}  ImageMagick no instalado. Creando icono básico...${NC}"
        echo -e "${YELLOW}  Para crear un mejor icono, instala: sudo apt install imagemagick${NC}"
        # Crear un PNG simple de 1x1 píxel (placehold
        echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > "$SCRIPT_DIR/icon.png"
        echo -e "${GREEN}✓ Icono básico creado${NC}"
    fi
    rm -f /tmp/icon.svg
else
    echo -e "${D}✓ Icono ya existe${NC}"
fi

# === 11. CREAR ACCESO DIRECTO EN EL ESCRITORIO ===
echo -e "\n${YELLOW}▶ ¿Crear acceso directo en el escritorio? (s/n)${NC}"
read -r crear_acceso
if [[ $crear_acceso == "s" || $crear_acceso == "S" ]]; then
    DESKTOP_FILE="$HOME/Desktop/sysmonitorpro.desktop"
    
    # Asegurar que existe la carpeta Desktop
    mkdir -p "$HOME/Desktop"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SysMonitorPro
Comment=Monitor de sistema avanzado
Exec=$SCRIPT_DIR/sysmonitor
Icon=$SCRIPT_DIR/icon.png
Terminal=true
Categories=System;Monitor;
StartupNotify=true
EOF
    chmod +x "$DESKTOP_FILE"
    echo -e "${GREEN}✓ Acceso directo creado en el escritorio${NC}"
    
    # También crear en el menú de aplicaciones
    mkdir -p "$HOME/.local/share/applications"
    MENU_FILE="$HOME/.local/share/applications/sysmonitorpro.desktop"
    cp "$DESKTOP_FILE" "$MENU_FILE"
    echo -e "${GREEN}✓ Acceso directo agregado al menú de aplicaciones${NC}"
fi

# === 12. LIMPIEZA DE ARCHIVOS DE WINDOWS ===
echo -e "\n${YELLOW}▶ Limpiando archivos específicos de Windows...${NC}"
rm -f *.bat 2>/dev/null || true
rm -f *.ps1 2>/dev/null || true
rm -f requirements-windows.txt 2>/dev/null || true
rm -f powershell.jpg 2>/dev/null || true
rm -f install-python-windows.bat 2>/dev/null || true
echo -e "${GREEN}✓ Archivos de Windows eliminados${NC}"

# === 13. PRUEBA RÁPIDA ===
echo -e "\n${YELLOW}▶ Probando instalación...${NC}"
if source venv/bin/activate && python3 -c "import psutil" 2>/dev/null; then
    echo -e "${GREEN}✓ Todo funciona correctamente${NC}"
else
    echo -e "${RED}✗ Error en la prueba${NC}"
fi

# === 14. FINAL ===
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Instalación completada!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Para ejecutar:${NC}"
echo -e "  ./sysmonitor                # Desde la carpeta del proyecto"
if [[ $instalar_global == "s" || $instalar_global == "S" ]]; then
    echo -e "  sysmonitor                  # Desde cualquier lugar"
fi
if [[ $crear_acceso == "s" || $crear_acceso == "S" ]]; then
    echo -e "  Hacer doble clic en el icono del escritorio"
fi
echo -e "\n${YELLOW}Para ver opciones:${NC}"
echo -e "  sysmonitor --help"
echo -e "\n${GREEN}¡Disfruta de SysMonitorPro! 🚀${NC}"
