```markdown
# ⚡ SysMonitorPro

**Monitor de sistema avanzado para Windows/Linux**

---

## ✨ Características

| Módulo | Detalle |
|---|---|
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


```
![windows](https://github.com/george0884/Sysmonitorpro/blob/009aea715ccec4b6ead8999db7f992f8eda04c13/powershell.jpg)

### 🐧 Linux (todas las distribuciones)


El instalador:
- Verifica/instala Python 3 y pip
- Instala `psutil` (dependencia principal)
- Pregunta por soporte opcional para GPU
- Crea configuración en `~/.config/sysmonitorpro/config.json`
- Pregunta si deseas el comando global `sysmonitor`

### 📦 Por distribución (Linux - manual)

#### 🟠 Debian / Ubuntu / Mint / Pop!_OS

```bash
# Clonar el repositorio
git clone https://github.com/george0884/sysmonitorpro.git
cd sysmonitorpro

# Dar permisos al instalador
chmod +x install.sh

# Ejecutar instalador
./install.sh

#Manualmente
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install psutil
```

#### 🔵 Arch Linux / Manjaro / EndeavourOS

```bash
sudo pacman -S python python-psutil
```

#### 🟢 Fedora / RHEL / AlmaLinux / Rocky Linux

```bash
sudo dnf install python3 python3-pip -y
pip3 install psutil
```

---

## 🚀 Ejecución

### 🪟 Windows
## 📦 Instalación

### 🪟 Windows 10 / 11

#### Requisitos previos

1. **Instalar Python** (3.8 o superior)
   - Descargar desde [python.org](https://www.python.org/downloads/)
   - **IMPORTANTE:** Marcar "Add Python to PATH" durante la instalación

2. **Abrir PowerShell como Administrador** y ejecutar:

```powershell
# Verificar Python
python --version

# Instalar dependencias principales
#puedes usar el script automaticon mas abajo, incluiido en el repo.
pip install psutil

# Instalar dependencias para temperaturas (opcional pero recomendado)
pip install wmi pywin32 GPUtil
```

3. **Instalar OpenHardwareMonitor** (necesario para temperaturas)
   - Descargar desde [openhardwaremonitor.org](https://openhardwaremonitor.org/)
   - Ejecutar el programa (debe quedar abierto en segundo plano)
   - Asegurarse de que muestra temperaturas en su interfaz

#### Instalar SysMonitorPro en Windows

```powershell
# Clonar o descargar el repositorio
git clone https://github.com/george0884/sysmonitorpro.git
cd sysmonitorpro
#instalador automatico dependencias
.\install-python-windows.bat
#install sysmonitor
.\install.bat

# Configurar PowerShell para ejecutar scripts (si es necesario)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Ejecutar el script
python sysmonitorpro.py
```

#### Crear acceso directo (opcional)

```powershell
# Crear archivo .bat para ejecutar fácilmente
echo python %~dp0sysmonitorpro.py > sysmonitor.bat

# O crear alias en PowerShell
New-Alias sysmonitor "python C:\ruta\sysmonitorpro.py"
```


```powershell
# Desde PowerShell o CMD
python sysmonitorpro.py

# Con opciones
python sysmonitorpro.py --json
python sysmonitorpro.py --no-gpu --no-top
python sysmonitorpro.py -i 2.0
```

### 🐧 Linux

```bash
# Modo directo
python3 sysmonitorpro.py

# Como comando global (si usaste el instalador)
sysmonitor

# Con permisos de ejecución
chmod +x sysmonitorpro.py
./sysmonitorpro.py
```

---

## 🎮 Controles

| Tecla | Acción |
|-------|--------|
| `q` / `Q` | Salir limpiamente |
| `Ctrl+R` | Forzar redimensionamiento y recarga de pantalla |

---

## ⚙️ Línea de comandos

| Opción | Descripción |
|--------|-------------|
| `--json` | Salida en formato JSON (para scripts) |
| `--no-gpu` | Ocultar sección GPU |
| `--no-disks` | Ocultar sección discos |
| `--no-network` | Ocultar sección red |
| `--no-top` | Ocultar top procesos |
| `-i N` / `--interval N` | Intervalo de actualización en segundos (ej: `-i 2.0`) |
| `-c ARCHIVO` / `--config ARCHIVO` | Usar archivo de configuración específico |
| `--hist-size N` | Tamaño del historial en segundos |
| `--help` | Mostrar ayuda |

### Ejemplos

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

## ⚙️ Configuración personalizada

El script busca configuración en:
- **Windows:** `%USERPROFILE%\.config\sysmonitorpro\config.json`
- **Linux:** `~/.config/sysmonitorpro/config.json`

Si no existe, usa valores por defecto.

### Crear configuración manualmente

#### Windows (PowerShell)
```powershell
mkdir $env:USERPROFILE\.config\sysmonitorpro
notepad $env:USERPROFILE\.config\sysmonitorpro\config.json
```

#### Linux (bash)
```bash
mkdir -p ~/.config/sysmonitorpro
nano ~/.config/sysmonitorpro/config.json
```

### Opciones disponibles

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

| Opción | Valores | Defecto | Descripción |
|--------|---------|---------|-------------|
| `intervalo` | 0.5 - 5.0 | 1.0 | Segundos entre actualizaciones |
| `mostrar_gpu` | true / false | true | Mostrar u ocultar sección GPU |
| `mostrar_discos` | true / false | true | Mostrar u ocultar discos |
| `mostrar_red` | true / false | true | Mostrar u ocultar red |
| `mostrar_top` | true / false | true | Mostrar u ocultar top procesos |
| `grafico_tamano` | 20 - 100 | 40 | Ancho del gráfico histórico |
| `historial_segundos` | 30 - 300 | 60 | Duración del historial |
| `interfaz_red` | "auto" / Nombre | "auto" | Interfaz específica |

---

## 🌡️ Sensores de temperatura

### Windows
- **Requisito:** OpenHardwareMonitor ejecutándose en segundo plano
- **Descargar:** [openhardwaremonitor.org](https://openhardwaremonitor.org/)
- Las temperaturas de CPU, GPU y discos aparecerán automáticamente

### Linux
SysMonitorPro detecta automáticamente:

| Sensor | Hardware |
|--------|----------|
| `k10temp` | AMD Ryzen / Threadripper |
| `coretemp` | Intel Core |
| `acpitz` | ACPI genérico |
| `cpu_thermal` | ARM / Raspberry Pi |
| `nvme` | Discos NVMe |

### Colores por temperatura

```
🔵 Azul     < 60°C   →  Normal
🟡 Amarillo  60-79°C →  Moderado
🔴 Rojo      ≥ 80°C   →  Crítico
```

---

## 🔌 Integración con otros programas

### Windows (PowerShell script)
```powershell
# Obtener métricas cada 5 segundos
while ($true) {
    python sysmonitorpro.py --json | Out-File -Append metrics.json
    Start-Sleep -Seconds 5
}
```

### i3blocks (Linux)
```ini
[sysmonitor]
command=sysmonitor --json | jq -r '"CPU: \(.cpu.percent)% RAM: \(.memory.ram.percent)%"'
interval=2
```

### Polybar (Linux)
```ini
[module/sysmonitor]
type = custom/script
exec = sysmonitor --json | jq -r '"CPU: \(.cpu.percent)%"'
interval = 2
```

### Cron (Linux - registro cada minuto)
```bash
*/1 * * * * /usr/local/bin/sysmonitor --json >> /var/log/sysmonitor.log
```

### tmux (Linux - barra de estado)
```bash
# En ~/.tmux.conf
set -g status-right "#(sysmonitor --json | jq -r '\"CPU: \\(.cpu.percent)%\"')"
```

---

## 📦 Compilado a binario (opcional)

### Windows (exe)
```powershell
# Instalar PyInstaller
pip install pyinstaller

# Compilar a .exe
pyinstaller --onefile --name sysmonitor.exe sysmonitorpro.py

# El ejecutable estará en ./dist/sysmonitor.exe
```

### Linux (binario)
```bash
pip3 install pyinstaller
pyinstaller --onefile --name sysmonitor sysmonitorpro.py
./dist/sysmonitor
sudo cp dist/sysmonitor /usr/local/bin/
```

> **Nota:** El binario pesa ~8-12 MB pero funciona sin necesidad de Python instalado.

---

## 🗂️ Estructura del proyecto

```
sysmonitorpro/
├── sysmonitorpro.py       # Script principal
├── install.sh             # Instalador automático (Linux)
├── setup.py               # Instalación con pip
├── .gitignore             # Archivos ignorados
├── LICENSE                # GPL-3.0
├── README.md              # Este archivo
└── config/
    ├── default.json       # Configuración por defecto
    └── example.json       # Ejemplo de configuración
```

---

## 🛠️ Requisitos del sistema

| Requisito | Windows | Linux |
|-----------|---------|-------|
| **SO** | Windows 10/11 | Cualquier distro moderna |
| **Python** | 3.8+ | 3.8+ |
| **psutil** | ✅ | ✅ |
| **wmi/pywin32** | Opcional (temperaturas) | ❌ |
| **OpenHardwareMonitor** | Opcional (temperaturas) | ❌ |
| **Terminal** | PowerShell, CMD, Windows Terminal | Cualquier terminal ANSI |

---

## ❓ Solución de problemas

### Windows

#### Error: `psutil not found`
```powershell
pip install psutil
```

#### Error: `No module named 'wmi'`
```powershell
pip install wmi pywin32
```

#### No se ven temperaturas en Windows
```powershell
# 1. Instalar OpenHardwareMonitor
# 2. Ejecutarlo (debe quedar abierto)
# 3. Reiniciar PowerShell
# 4. Volver a ejecutar el script
```

#### Los colores no se ven en PowerShell
```powershell
# Usar Windows Terminal (recomendado)
# O activar colores ANSI en PowerShell:
Set-ItemProperty HKCU:\Console VirtualTerminalLevel -Type DWord -Value 1
```

### Linux

#### Error: `psutil not found`
```bash
pip3 install --user psutil
# o en sistemas sin --user
pip3 install psutil --break-system-packages
```

#### No se ven temperaturas
```bash
sudo apt install lm-sensors
sudo sensors-detect
```

#### No se detecta GPU NVIDIA
```bash
nvidia-smi  # Debe mostrar información
# Si no funciona, instalar drivers NVIDIA
```

#### El comando `sysmonitor` no se encuentra
```bash
# Reabrir la terminal o ejecutar:
source ~/.bashrc

# O agregar manualmente al PATH:
export PATH="$HOME/.local/bin:$PATH"
```

---

## 📝 Licencia

**GNU General Public License v3.0** — libre de usar, modificar y distribuir.

---

<div align="center">

**Hecho con 🖤 para la terminal**

```
sysmonitor --help
```


</div>
```

## ✅ **Resumen de cambios en el README:**

| Sección | Cambio |
|---------|--------|
| Título | Ahora dice "Windows/Linux" |
| Instalación | Nueva sección completa para Windows 10/11 |
| Ejecución | Comandos para PowerShell/CMD |
| Configuración | Ruta para Windows (`%USERPROFILE%`) |
| Integración | Ejemplo para PowerShell |
| Compilado | Instrucciones para crear `.exe` |
| Requisitos | Tabla comparativa Windows/Linux |
| Solución de problemas | Sección específica para Windows
