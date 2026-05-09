
```markdown
# ⚡ SysMonitorPro

```
# Generar ASCII art con figlet
figlet -f standard "SysMonitorPro"

```

> **Monitor de sistema en tiempo real para Linux** — CPU por núcleo, temperatura, frecuencia, RAM, SWAP, red con velocidad instantánea, discos, procesos, gráficos históricos y salida JSON. Todo en terminal, sin dependencias pesadas.

---

## ✨ Características

| Módulo | Detalle |
|---|---|
| **CPU** | Uso real por núcleo · Frecuencia GHz · Temperatura con colores |
| **Temperatura** | Soporte Intel (`coretemp`) · AMD (`k10temp`) · ACPI · NVMe · Auto-detección |
| **RAM / SWAP** | Uso en tiempo real con barras de progreso |
| **Red** | Velocidad ↓ / ↑ instantánea · Total acumulado · Detección automática de interfaz activa |
| **Discos** | Uso por partición · Bytes leídos/escritos |
| **Procesos** | Top procesos ordenados por CPU% · PID · MEM% · Usuario |
| **Gráficos históricos** | Visualización ASCII del uso de CPU y RAM (últimos 60 segundos) |
| **GPU** | Soporte NVIDIA (nvidia-smi), AMD (ROCm / sysfs), Intel (sysfs) |
| **Modo JSON** | Salida estructurada para scripts, i3blocks, polybar, cron |
| **UI** | Pantalla alternativa · Cursor oculto · Redimensionamiento dinámico · Salida limpia |
```
---

## 📦 Instalación

### 🔵 Para todas las distribuciones (recomendado)

```bash
# Clonar el repositorio
git clone https://github.com/george0884/sysmonitorpro.git
cd sysmonitorpro

# Dar permisos al instalador
chmod +x install.sh

# Ejecutar instalador
./install.sh
```

El instalador:

· Verifica/instala Python 3 y pip
· Instala psutil (dependencia principal)
· Pregunta por soporte opcional para GPU
· Crea configuración en ~/.config/sysmonitorpro/config.json
· Pregunta si deseas el comando global sysmonitor

🟠 Debian / Ubuntu / Mint / Pop!_OS (manual)

```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install psutil
```

🔵 Arch Linux / Manjaro / EndeavourOS (manual)

```bash
sudo pacman -S python python-psutil
```

🟢 Fedora / RHEL / AlmaLinux / Rocky Linux (manual)

```bash
sudo dnf install python3 python3-pip -y
pip3 install psutil
```

---

🚀 Ejecución

Modo directo

```bash
python3 sysmonitorpro.py
```

Como comando global (si usaste el instalador)

```bash
sysmonitor
```

Con permisos de ejecución (sin instalador)

```bash
chmod +x sysmonitorpro.py
./sysmonitorpro.py
```

Instalación manual global (alternativa)

```bash
sudo cp sysmonitorpro.py /usr/local/bin/sysmonitor
sudo chmod +x /usr/local/bin/sysmonitor
```

---

🎮 Controles

Tecla Acción
q / Q Salir limpiamente
Ctrl+R Forzar redimensionamiento y recarga de pantalla

---

⚙️ Línea de comandos

Opción Descripción
--json Salida en formato JSON (para scripts)
--no-gpu Ocultar sección GPU
--no-disks Ocultar sección discos
--no-network Ocultar sección red
--no-top Ocultar top procesos
-i N / --interval N Intervalo de actualización en segundos (ej: -i 2.0)
-c ARCHIVO / --config ARCHIVO Usar archivo de configuración específico
--hist-size N Tamaño del historial en segundos
--help Mostrar ayuda

Ejemplos

```bash
# Modo JSON para scripts
sysmonitor --json

# Ocultar GPU y discos
sysmonitor --no-gpu --no-disks

# Intervalo de 2 segundos
sysmonitor -i 2.0

# Usar configuración personalizada
sysmonitor -c ~/mi-config.json
```

---

⚙️ Configuración personalizada

El script busca configuración en ~/.config/sysmonitorpro/config.json. Si no existe, usa valores por defecto.

Crear configuración manualmente

```bash
mkdir -p ~/.config/sysmonitorpro
nano ~/.config/sysmonitorpro/config.json
```

Opciones disponibles

```json
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
```

Opción Valores Defecto Descripción
intervalo 0.5 - 5.0 1.0 Segundos entre actualizaciones
mostrar_gpu true / false true Mostrar u ocultar sección GPU
mostrar_discos true / false true Mostrar u ocultar discos
mostrar_red true / false true Mostrar u ocultar red
mostrar_top true / false true Mostrar u ocultar top procesos
grafico_tamano 20 - 100 40 Ancho del gráfico histórico en caracteres
historial_segundos 30 - 300 60 Duración del historial en segundos
interfaz_red "auto" / Nombre "auto" Interfaz específica o detección automática

---

🌡️ Sensores de temperatura soportados

SysMonitorPro detecta automáticamente el sensor disponible:

Sensor Hardware
k10temp AMD Ryzen / Threadripper
coretemp Intel Core
acpitz ACPI genérico
cpu_thermal ARM / Raspberry Pi
pch_skylake Intel PCH
nvme Discos NVMe
iwlwifi WiFi Intel

Colores por temperatura:

```
🔵 Azul     < 60°C   →  Normal
🟡 Amarillo  60-79°C →  Moderado
🔴 Rojo      ≥ 80°C   →  Crítico
```

---

🔌 Integración con otros programas

i3blocks

```ini
[sysmonitor]
command=sysmonitor --json | jq -r '"CPU: \(.cpu.percent)% RAM: \(.memory.ram.percent)%"'
interval=2
```

Polybar

```ini
[module/sysmonitor]
type = custom/script
exec = sysmonitor --json | jq -r '"CPU: \(.cpu.percent)%"'
interval = 2
```

Cron (registro cada minuto)

```bash
*/1 * * * * /usr/local/bin/sysmonitor --json >> /var/log/sysmonitor.log
```

tmux (en barra de estado)

```bash
# En ~/.tmux.conf
set -g status-right "#(sysmonitor --json | jq -r '\"CPU: \\(.cpu.percent)%\"')"
```

---

📦 Compilado a binario (opcional)

Si prefieres un ejecutable standalone sin necesidad de Python:

Instalar PyInstaller

```bash
pip3 install pyinstaller
```

Compilar

```bash
pyinstaller --onefile --name sysmonitor sysmonitorpro.py
```

Ejecutar

```bash
./dist/sysmonitor
sudo cp dist/sysmonitor /usr/local/bin/
```

Nota: El binario pesa ~8-12 MB pero funciona en sistemas sin Python instalado.

---

🗂️ Estructura del proyecto

```
sysmonitorpro/
├── sysmonitorpro.py       # Script principal
├── install.sh             # Instalador automático
├── setup.py               # Instalación con pip
├── .gitignore             # Archivos ignorados
├── LICENSE                # GPL-3.0
├── README.md              # Este archivo
└── config/
    ├── default.json       # Configuración por defecto
    └── example.json       # Ejemplo de configuración
```

---

🛠️ Requisitos del sistema

Requisito Detalle
Sistema operativo Linux (cualquier distro moderna)
Python 3.8 o superior
psutil 5.8.0 o superior
Terminal Con soporte ANSI/256 colores (GNOME Terminal, Alacritty, Kitty, Konsole, WezTerm, xterm)
Permisos Usuario normal (no requiere root)

---

❓ Solución de problemas

Error: psutil not found

```bash
pip3 install --user psutil
# o en sistemas sin --user
pip3 install psutil --break-system-packages
```

No se ven temperaturas

```bash
sudo apt install lm-sensors
sudo sensors-detect
```

No se detecta GPU NVIDIA

```bash
nvidia-smi  # Debe mostrar información
# Si no funciona, instalar drivers NVIDIA
```

El comando sysmonitor no se encuentra

```bash
# Reabrir la terminal o ejecutar:
source ~/.bashrc

# O agregar manualmente al PATH:
export PATH="$HOME/.local/bin:$PATH"
```

---

📝 Licencia

GNU General Public License v3.0 — libre de usar, modificar y distribuir.

---

<div align="center">

Hecho con 🖤 para la terminal

```
sysmonitor --help
```

</div>
```
