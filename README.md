```markdown
# ⚡ SysMonitorPro

**Monitor de sistema avanzado para Windows/Linux**

---

## ✨ Características

| Módulo | Detalle |
|--------|---------|
| **CPU** | Uso real por núcleo · Frecuencia GHz · Temperatura con colores |
| **Temperatura** | Soporte Intel, AMD, NVMe, GPU (Windows via OpenHardwareMonitor) |
| **RAM / SWAP** | Uso en tiempo real con barras de progreso |
| **Red** | Velocidad ↓ / ↑ instantánea · Total acumulado · Detección automática |
| **Discos** | Uso por partición · Bytes leídos/escritos |
| **Procesos** | Top procesos ordenados por CPU% · PID · MEM% · Usuario |
| **Gráficos históricos** | Visualización ASCII del uso de CPU y RAM (últimos 60 segundos) |
| **GPU** | Soporte NVIDIA, AMD, Intel |
| **Modo JSON** | Salida estructurada para scripts |
| **UI** | Pantalla alternativa · Cursor oculto · Redimensionamiento dinámico |

---
## 📸 Capturas

<div align="center">
  
### 🐧 Linux
<img src="https://raw.githubusercontent.com/george0884/Sysmonitorpro/47a87de7c20065e38f3af142189b2c8c9b2ad592/Linux.png" alt="Linux" width="800"/>

### 🪟 Windows
<img src="https://raw.githubusercontent.com/george0884/Sysmonitorpro/009aea715ccec4b6ead8999db7f992f8eda04c13/powershell.jpg" alt="Windows" width="800"/>

</div>

---

## 🚀 Instalación rápida

### 🐧 Linux (todas las distribuciones)


El instalador:

· ✅ Verifica/instala Python 3 y pip
· ✅ Instala psutil (dependencia principal)
· ✅ Pregunta por soporte opcional para GPU
· ✅ Crea configuración en ~/.config/sysmonitorpro/config.json
· ✅ Pregunta si deseas el comando global sysmonitor
```

#### Desinstalador interactivo seguro

```bash
chmod +x uninstall.sh
./uninstall.sh
```
#### Instalador automático (recomendado)

```bash
git clone https://github.com/george0884/sysmonitorpro.git && \
cd sysmonitorpro && \
chmod +x install.sh && \
./install.sh
```

Instalación manual por distribución

🟠 Debian / Ubuntu / Mint / Pop!_OS

```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install psutil
```

🔵 Arch Linux / Manjaro / EndeavourOS

```bash
sudo pacman -S python python-psutil
```

🟢 Fedora / RHEL / AlmaLinux / Rocky Linux

```bash
sudo dnf install python3 python3-pip -y
pip3 install psutil
```

---

🪟 Windows 10 / 11

Requisitos previos

1. Instalar Python (3.8 o superior) desde python.org
      ⚠️ Importante: Marcar "Add Python to PATH" durante la instalación
2. Abrir PowerShell como Administrador y ejecutar:

```powershell
# Verificar Python
python --version

# Instalar dependencias principales
pip install psutil

# Dependencias opcionales para temperaturas
pip install wmi pywin32 GPUtil
```

1. Instalar OpenHardwareMonitor (necesario para temperaturas)
      Descargar desde openhardwaremonitor.org
      Debe quedar ejecutándose en segundo plano.

Instalar SysMonitorPro

```powershell
git clone https://github.com/george0884/sysmonitorpro.git
cd sysmonitorpro

# Instalador automático de dependencias
.\install-python-windows.bat

# Instalador principal
.\install.bat

# Configurar PowerShell para ejecutar scripts (si es necesario)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Crear acceso directo (opcional)

```powershell
# Archivo .bat
echo python %~dp0sysmonitorpro.py > sysmonitor.bat

# Alias en PowerShell
New-Alias sysmonitor "python C:\ruta\sysmonitorpro.py"
```

---

📦 Ejecutable standalone (recomendado)

No necesitas Python instalado. Descarga y ejecuta:

```bash
wget https://github.com/george0884/Sysmonitorpro/releases/download/v1.0.0/sysmonitor
chmod +x sysmonitor
./sysmonitor
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
-i N / --interval N Intervalo de actualización (ej: -i 2.0)
-c ARCHIVO / --config ARCHIVO Usar configuración específica
--hist-size N Tamaño del historial (segundos)
--help Mostrar ayuda

Ejemplos

```bash
sysmonitor --json                     # Modo JSON
sysmonitor --no-gpu --no-disks        # Ocultar GPU y discos
sysmonitor -i 2.0                     # Actualizar cada 2 segundos
sysmonitor -c ~/mi-config.json        # Configuración personalizada
```

---

⚙️ Configuración personalizada

Ubicación de la configuración:

· Windows: %USERPROFILE%\.config\sysmonitorpro\config.json
· Linux: ~/.config/sysmonitorpro/config.json

Crear configuración manualmente

Windows (PowerShell)

```powershell
mkdir $env:USERPROFILE\.config\sysmonitorpro
notepad $env:USERPROFILE\.config\sysmonitorpro\config.json
```

Linux (bash)

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
mostrar_gpu true/false true Mostrar/ocultar GPU
mostrar_discos true/false true Mostrar/ocultar discos
mostrar_red true/false true Mostrar/ocultar red
mostrar_top true/false true Mostrar/ocultar top procesos
grafico_tamano 20 - 100 40 Ancho del gráfico histórico
historial_segundos 30 - 300 60 Duración del historial
interfaz_red "auto" / nombre "auto" Interfaz específica

---

🌡️ Sensores de temperatura

Windows

· Requisito: OpenHardwareMonitor ejecutándose
· Descarga: openhardwaremonitor.org

Linux

Detecta automáticamente:

Sensor Hardware
k10temp AMD Ryzen / Threadripper
coretemp Intel Core
acpitz ACPI genérico
cpu_thermal ARM / Raspberry Pi
nvme Discos NVMe

Colores por temperatura

```
🔵 Azul     < 60°C   →  Normal
🟡 Amarillo  60-79°C →  Moderado
🔴 Rojo      ≥ 80°C   →  Crítico
```

---

🔌 Integración con otros programas

Windows (PowerShell)

```powershell
while ($true) {
    python sysmonitorpro.py --json | Out-File -Append metrics.json
    Start-Sleep -Seconds 5
}
```

i3blocks (Linux)

```ini
[sysmonitor]
command=sysmonitor --json | jq -r '"CPU: \(.cpu.percent)% RAM: \(.memory.ram.percent)%"'
interval=2
```

Polybar (Linux)

```ini
[module/sysmonitor]
type = custom/script
exec = sysmonitor --json | jq -r '"CPU: \(.cpu.percent)%"'
interval = 2
```

Cron (Linux)

```bash
*/1 * * * * /usr/local/bin/sysmonitor --json >> /var/log/sysmonitor.log
```

tmux

```bash
set -g status-right "#(sysmonitor --json | jq -r '\"CPU: \\(.cpu.percent)%\"')"
```

---

📦 Compilado a binario (opcional)

Windows (.exe)

```powershell
pip install pyinstaller
pyinstaller --onefile --name sysmonitor.exe sysmonitorpro.py
# El ejecutable estará en ./dist/sysmonitor.exe
```

Linux (binario)

```bash
pip install pyinstaller
pyinstaller --onefile --name sysmonitor sysmonitorpro.py
./dist/sysmonitor
sudo cp dist/sysmonitor /usr/local/bin/
```

Nota: El binario pesa ~8-12 MB y no requiere Python.

---

🗂️ Estructura del proyecto

```
sysmonitorpro/
├── sysmonitorpro.py       # Script principal
├── install.sh             # Instalador Linux
├── install.bat            # Instalador Windows
├── uninstall.sh           # Desinstalador Linux
├── setup.py               # Instalación con pip
├── .gitignore
├── LICENSE                # GPL-3.0
├── README.md
└── config/
    ├── default.json
    └── example.json
```

---

🛠️ Requisitos del sistema

Requisito Windows Linux
SO Windows 10/11 Cualquier distro moderna
Python 3.8+ 3.8+
psutil ✅ ✅
wmi/pywin32 Opcional (temperaturas) ❌
OpenHardwareMonitor Opcional (temperaturas) ❌
Terminal PowerShell, CMD, Windows Terminal Cualquier terminal ANSI

---

❓ Solución de problemas

Windows

Problema Solución
psutil not found pip install psutil
No module named 'wmi' pip install wmi pywin32
No se ven temperaturas Instala y ejecuta OpenHardwareMonitor
Colores no visibles Usa Windows Terminal o ejecuta: Set-ItemProperty HKCU:\Console VirtualTerminalLevel -Type DWord -Value 1

Linux

Problema Solución
psutil not found pip3 install --user psutil
No se ven temperaturas sudo apt install lm-sensors && sudo sensors-detect
No detecta GPU NVIDIA Instalar drivers NVIDIA y verificar con nvidia-smi
sysmonitor no se encuentra source ~/.bashrc o export PATH="$PATH:$HOME/.local/bin"

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

---
