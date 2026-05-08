# ⚡ SysMonitorPro

```
███████╗██╗   ██╗███████╗███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗ ██████╗ ██████╗  ██████╗
██╔════╝╚██╗ ██╔╝██╔════╝████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗
███████╗ ╚████╔╝ ███████╗██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝██████╔╝██████╔╝██║   ██║
╚════██║  ╚██╔╝  ╚════██║██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔═══╝ ██╔══██╗██╔═══╝ ██║   ██║
███████║   ██║   ███████║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║     ██║  ██║██║     ╚██████╔╝
╚══════╝   ╚═╝   ╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝      ╚═════╝
```

> **Monitor de sistema en tiempo real para Linux** — CPU por núcleo, temperatura, frecuencia, RAM, SWAP, red con velocidad instantánea, discos y procesos. Todo en terminal, sin dependencias pesadas.

---

## ✨ Características

| Módulo | Detalle |
|---|---|
| **CPU** | Uso real por núcleo · Frecuencia GHz · Temperatura con colores |
| **Temperatura** | Soporte Intel (`coretemp`) · AMD (`k10temp`) · ACPI · Auto-detección |
| **RAM / SWAP** | Uso en tiempo real con barras de progreso |
| **Red** | Velocidad ↓ / ↑ instantánea en MB/s · Total acumulado |
| **Discos** | Uso por partición · Bytes leídos/escritos |
| **Procesos** | Top procesos ordenados por CPU% · PID · MEM% · Usuario |
| **UI** | Pantalla alternativa · Cursor oculto · Salida limpia con `q` |

---

## 📦 Dependencias

# Ejecución normal
python3 sysmonitorpro_plus.py

# Modo JSON
python3 sysmonitorpro_plus.py --json > stats.json

# Ocultar secciones específicas
python3 sysmonitorpro_plus.py --no-gpu --no-top

# Intervalo personalizado
python3 sysmonitorpro_plus.py -i 2.0

# Configuración personalizada
python3 sysmonitorpro_plus.py -c ~/mi_config.json

# Ayuda
python3 sysmonitorpro_plus.py --help

El único requisito externo es **psutil**. Python 3.8+ viene preinstalado en todas las distros modernas.

### 🟠 Debian / Ubuntu / Mint / Pop!_OS

```bash
# Instalar Python y pip si no están presentes
sudo apt update
sudo apt install python3 python3-pip -y

# Instalar psutil
pip3 install psutil

# Alternativa: instalar desde repositorio oficial (sin pip)
sudo apt install python3-psutil -y
```

### 🔵 Arch Linux / Manjaro / EndeavourOS

```bash
# Instalar Python y psutil desde repos oficiales
sudo pacman -S python python-psutil

# Alternativa con pip (entorno virtual recomendado en Arch)
sudo pacman -S python python-pip
pip install psutil --break-system-packages
```

### 🟢 Fedora / RHEL / AlmaLinux / Rocky Linux

```bash
# Instalar Python y pip
sudo dnf install python3 python3-pip -y

# Instalar psutil
pip3 install psutil

# Alternativa desde repositorio
sudo dnf install python3-psutil -y
```

---

## 🚀 Ejecución

### Modo directo

```bash
python3 sysmonitorpro.py
```

### Con permisos de ejecución

```bash
chmod +x sysmonitorpro.py
./sysmonitorpro.py
```

### Como comando global del sistema

```bash
sudo cp sysmonitorpro.py /usr/local/bin/sysmonitorpro
sudo chmod +x /usr/local/bin/sysmonitorpro

# Ejecutar desde cualquier lugar
sysmonitorpro
```

---

## 📦 Compilado a binario (opcional)

Si preferís distribuir el script como un ejecutable standalone sin necesidad de Python instalado, podés compilarlo con **PyInstaller**.

### Instalar PyInstaller

```bash
# Debian / Ubuntu
pip3 install pyinstaller

# Arch Linux
sudo pacman -S python-pyinstaller
# o
pip install pyinstaller --break-system-packages

# Fedora
pip3 install pyinstaller
```

### Compilar

```bash
# Binario simple (un archivo ejecutable)
pyinstaller --onefile --name sysmonitorpro sysmonitorpro.py

# El binario queda en:
./dist/sysmonitorpro
```

### Ejecutar el binario compilado

```bash
./dist/sysmonitorpro

# Instalar globalmente
sudo cp dist/sysmonitorpro /usr/local/bin/
sysmonitorpro
```

> **Nota:** El binario compilado incluye el intérprete Python y psutil. Funciona en sistemas sin Python instalado, pero el archivo pesa ~8–12 MB.

---

## 🎮 Controles

| Tecla | Acción |
|---|---|
| `q` / `Q` | Salir limpiamente |

---

## 🌡️ Sensores de temperatura soportados

SysMonitorPro detecta automáticamente el sensor disponible en el siguiente orden de prioridad:

```
k10temp     →  AMD Ryzen / Threadripper
coretemp    →  Intel Core
acpitz      →  ACPI genérico
cpu_thermal →  ARM / SBCs (Raspberry Pi, etc.)
```

Los valores se muestran con codificación de color:

```
🟦 Azul celeste   < 60°C   Normal
🟨 Amarillo       60–79°C  Moderado
🟥 Rojo           ≥ 80°C   Crítico
```

---

## 🗂️ Estructura del proyecto

```
sysmonitorpro/
├── sysmonitorpro.py   # Script principal
└── README.md          # Este archivo
```

---

## 🛠️ Requisitos del sistema

- **OS:** Linux (cualquier distro moderna)
- **Python:** 3.8 o superior
- **psutil:** 5.8.0 o superior
- **Terminal:** Con soporte ANSI/256 colores (la mayoría: GNOME Terminal, Alacritty, Kitty, Konsole, WezTerm, xterm)

---

## 📝 Licencia

MIT — libre para usar, modificar y distribuir.

---

<div align="center">

**Hecho con 🖤 para la terminal**

`python3 sysmonitorpro.py`

</div>
