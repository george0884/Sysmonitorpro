#!/usr/bin/env python3
"""
sysmonitorpro.py — Monitor de sistema avanzado para Windows/Linux

Todas las lecturas son reales: si un sensor no está disponible se muestra
"N/A" en lugar de inventar un valor.
"""

import os
import re
import sys
import json
import glob
import time
import heapq
import signal
import shutil
import socket
import argparse
import subprocess
import platform
import threading
import atexit
from collections import deque

# ─── DETECTAR SISTEMA OPERATIVO ────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# ─── ACTIVAR COLORES ANSI EN WINDOWS ────────────────────────────────────────
if IS_WINDOWS:
    os.system("")
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

try:
    import psutil
except ImportError:
    print("Error: psutil no instalado. Ejecuta: pip install psutil")
    sys.exit(1)

# ─── IMPORTAR DEPENDENCIAS WINDOWS ──────────────────────────────────────────
if IS_WINDOWS:
    try:
        import wmi
        HAS_WMI = True
    except ImportError:
        HAS_WMI = False

    try:
        import GPUtil
        HAS_GPUTIL = True
    except ImportError:
        HAS_GPUTIL = False
else:
    HAS_WMI = False
    HAS_GPUTIL = False

# ─── COLORES ANSI ────────────────────────────────────────────────────────────
M      = "\033[38;5;201m"
C      = "\033[38;5;51m"
C_BAR  = "\033[38;5;39m"
C_SHD  = "\033[38;5;240m"
W      = "\033[1;37m"
D      = "\033[2;37m"
G      = "\033[38;5;46m"
Y      = "\033[38;5;226m"
R      = "\033[38;5;196m"
NC     = "\033[0m"

CONFIG_DEFECTO = {
    "intervalo": 1.0,
    "mostrar_gpu": True,
    "mostrar_discos": True,
    "mostrar_red": True,
    "mostrar_top": True,
    "mostrar_fps": True,
    "interfaz_red": "auto",
    "presentmon": "",          # Windows: ruta a PresentMon.exe (vacío = buscar)
    "mangohud_logs": "",       # Linux: carpeta de registros de MangoHud (vacío = auto)
}
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".config", "sysmonitorpro", "config.json")

resize_event = threading.Event()

# ─── SALIDA LIMPIA ───────────────────────────────────────────────────────────
def salir(sig=None, frame=None):
    sys.stdout.write("\033[?1049l\033[?25h")
    sys.stdout.flush()
    sys.exit(0)

def handle_winch(sig=None, frame=None):
    resize_event.set()

# ─── UTILIDADES ──────────────────────────────────────────────────────────────
def barra(pct: float, ancho: int = 12) -> str:
    pct = max(0.0, min(100.0, pct))
    rell = int(pct * ancho / 100)
    vac = ancho - rell
    col = C_BAR if pct < 80 else (Y if pct < 90 else R)
    # La parte vacía usa un carácter fino en vez de bloques grises sólidos:
    # con terminales transparentes (Alacritty, Konsole) los bloques tapaban el fondo.
    return f"{D}[{NC}{col}{'█' * rell}{NC}{C_SHD}{'─' * vac}{NC}{D}]{NC} {C}{pct:5.1f}%{NC}"

def barra_na(ancho: int = 12) -> str:
    return f"{D}[{'·' * ancho}]{NC} {D}  N/A{NC}"

def color_temp(t: float) -> str:
    if t is None:
        return D
    if t < 60:
        return C
    if t < 80:
        return Y
    return R

def fmt_temp(t) -> str:
    if t is None:
        return ""
    return f"  {color_temp(t)}{t:.0f}°C{NC}"

def humanize(n: float, suffix="") -> str:
    if not n:
        return f"  0.0{suffix}"
    for unit in ("", "K", "M", "G", "T"):
        if abs(n) < 1024.0:
            return f"{n:5.1f}{unit}{suffix}"
        n /= 1024.0
    return f"{n:.1f}P{suffix}"

def sep(cols: int) -> str:
    return f"{D}{'─' * min(cols, 65)}{NC}"

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def leer(path: str, defecto=None):
    """Lee un archivo de sysfs/procfs y devuelve su contenido sin espacios."""
    try:
        with open(path) as f:
            return f.read().strip()
    except (OSError, ValueError):
        return defecto

def leer_int(path: str, defecto=None):
    v = leer(path)
    try:
        return int(v)
    except (TypeError, ValueError):
        return defecto

def cache_ttl(ttl: float):
    """Cachea el resultado de una función durante `ttl` segundos (por argumentos).
    Evita lanzar subprocesos / consultas WMI caras en cada refresco."""
    def deco(fn):
        estado = {}
        def wrapper(*args):
            ahora = time.monotonic()
            t, v = estado.get(args, (None, None))
            if t is None or ahora - t >= ttl:
                v = fn(*args)
                estado[args] = (ahora, v)
            return v
        return wrapper
    return deco

class Tasa:
    """Convierte contadores acumulados (bytes) en velocidades por segundo."""
    def __init__(self):
        self.prev = {}
        self.t = None

    def calc(self, valores: dict) -> dict:
        ahora = time.monotonic()
        dt = (ahora - self.t) if self.t else 0
        res = {}
        for k, v in valores.items():
            p = self.prev.get(k)
            if p is None or dt <= 0:
                res[k] = tuple(0.0 for _ in v)
            else:
                # max(0, ...) por si el contador se reinicia (disco reconectado)
                res[k] = tuple(max(0.0, (a - b) / dt) for a, b in zip(v, p))
        self.prev = valores
        self.t = ahora
        return res

def run(cmd, timeout=2) -> str:
    try:
        return subprocess.check_output(cmd, timeout=timeout,
                                       stderr=subprocess.DEVNULL).decode(errors="ignore")
    except Exception:
        return ""

# ─── WMI (WINDOWS) ──────────────────────────────────────────────────────────
# Crear una conexión WMI tarda cientos de ms: se reutiliza y, si falla
# (p. ej. LibreHardwareMonitor aún no está abierto), se reintenta cada 30 s.
_wmi_conns = {}

def wmi_conn(namespace="root\\cimv2"):
    if not HAS_WMI:
        return None
    conn, t = _wmi_conns.get(namespace, (None, None))
    if conn is None and (t is None or time.monotonic() - t > 30):
        try:
            conn = wmi.WMI(namespace=namespace)
        except Exception:
            conn = None
        _wmi_conns[namespace] = (conn, time.monotonic())
    return conn

def wmi_reset(namespace):
    _wmi_conns[namespace] = (None, time.monotonic())

@cache_ttl(0.5)
def sensores_lhm():
    """Una única consulta por refresco a LibreHardwareMonitor (o al antiguo
    OpenHardwareMonitor). Devuelve [(hardware, tipo, nombre, valor)], donde
    hardware es p. ej. '/intelcpu/0', '/gpu-nvidia/0', '/nvme/1'."""
    for ns in ("root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor"):
        c = wmi_conn(ns)
        if c is None:
            continue
        try:
            res = []
            for s in c.Sensor():
                ident = s.Identifier or ""
                hw = s.Parent or ident.rsplit("/", 2)[0]
                res.append((hw.lower(), s.SensorType or "", s.Name or "", s.Value))
            if res:
                return res
        except Exception:
            wmi_reset(ns)
    return []

# ─── INFORMACIÓN DEL SISTEMA ─────────────────────────────────────────────────
def limpiar_dmi(v):
    if not v or v in ("To be filled by O.E.M.", "Default string", "System Product Name", "x.x"):
        return None
    return v

def get_system_info():
    info = {"hostname": platform.node()}

    if IS_WINDOWS:
        info["os"] = f"Windows {platform.release()}"
        info["kernel"] = platform.version()
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\BIOS")
            vendor = winreg.QueryValueEx(key, "BaseBoardManufacturer")[0]
            product = winreg.QueryValueEx(key, "BaseBoardProduct")[0]
            winreg.CloseKey(key)
            info["mb"] = " ".join(p for p in (limpiar_dmi(vendor), limpiar_dmi(product)) if p) or "Motherboard"
        except Exception:
            info["mb"] = "Motherboard"
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            info["cpu_model"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            winreg.CloseKey(key)
        except Exception:
            info["cpu_model"] = platform.processor() or "CPU"
    else:
        info["os"] = "Linux"
        for line in (leer("/etc/os-release", "") or "").splitlines():
            if line.startswith("PRETTY_NAME"):
                info["os"] = line.split("=", 1)[1].strip().strip('"')
                break
        info["kernel"] = platform.release()

        partes = [limpiar_dmi(leer(f"/sys/class/dmi/id/board_{k}")) for k in ("vendor", "name")]
        version = limpiar_dmi(leer("/sys/class/dmi/id/board_version"))
        if version:
            # Algunas placas ya traen "Rev X" (antes salía "Rev.Rev X")
            partes.append(version if version.lower().startswith("rev") else f"Rev.{version}")
        info["mb"] = (" ".join(p for p in partes if p) or "Motherboard")[:50]

        info["cpu_model"] = "CPU"
        for line in (leer("/proc/cpuinfo", "") or "").splitlines():
            # "model name" en x86, "Model" en Raspberry Pi / ARM
            if line.startswith(("model name", "Model")):
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break

    info["cores"] = psutil.cpu_count(logical=False) or 1
    info["threads"] = psutil.cpu_count(logical=True) or 1
    info["core_map"] = mapa_cores(info["cores"], info["threads"])
    return info

def mapa_cores(cores: int, threads: int):
    """Para cada CPU lógica, el id del núcleo físico al que pertenece.
    Sirve para asignar la temperatura 'Core N' a cada hilo."""
    if IS_LINUX:
        mapa = []
        for i in range(threads):
            mapa.append(leer_int(f"/sys/devices/system/cpu/cpu{i}/topology/core_id"))
        return mapa
    smt = max(1, threads // max(1, cores))
    return [i // smt for i in range(threads)]

# ─── TEMPERATURAS CPU ───────────────────────────────────────────────────────
CPU_CHIPS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "cpu-thermal",
             "soc_thermal", "thinkpad", "acpitz")

def get_cpu_temps_linux():
    """Devuelve (temp_global, {core_id: temp})."""
    try:
        sensores = psutil.sensors_temperatures()
    except Exception:
        return None, {}

    for chip in CPU_CHIPS:
        entradas = [e for e in sensores.get(chip, []) if 0 < e.current < 125]
        if not entradas:
            continue
        por_core = {}
        paquete = tdie = tctl = None
        for e in entradas:
            label = e.label or ""
            if label.startswith("Core "):              # Intel coretemp
                try:
                    por_core[int(label.split()[1])] = e.current
                except ValueError:
                    pass
            elif label.startswith("Package id"):
                paquete = max(paquete or 0, e.current)
            elif label == "Tdie":                       # AMD: temperatura real
                tdie = e.current
            elif label == "Tctl":                       # AMD: puede llevar offset
                tctl = e.current
        global_t = paquete or tdie or tctl
        if global_t is None:
            global_t = max(e.current for e in entradas)
        return global_t, por_core
    return None, {}

def get_cpu_temps_windows():
    global_t = None
    por_core = {}
    otros = []
    for hw, tipo, nombre, valor in sensores_lhm():
        if tipo != "Temperature" or valor is None or "cpu" not in hw:
            continue
        m = re.match(r"CPU Core #(\d+)$", nombre)
        if m:
            por_core[int(m.group(1)) - 1] = valor
        elif nombre in ("CPU Package", "Core (Tctl/Tdie)", "Core (Tdie)", "Core (Tctl)", "CPU (Tctl/Tdie)"):
            global_t = max(global_t or 0, valor)
        else:
            otros.append(valor)
    if global_t is None and (por_core or otros):
        global_t = max(list(por_core.values()) + otros)
    if global_t is None:
        global_t = temp_acpi_windows()
    return global_t, por_core

@cache_ttl(5)
def temp_acpi_windows():
    """Último recurso sin LHM: zona térmica ACPI (requiere administrador y no
    todas las placas la exponen; suele medir la placa, no el núcleo)."""
    c = wmi_conn("root\\wmi")
    if c is None:
        return None
    try:
        temps = [z.CurrentTemperature / 10.0 - 273.15 for z in c.MSAcpi_ThermalZoneTemperature()]
        temps = [t for t in temps if 0 < t < 125]
        return max(temps) if temps else None
    except Exception:
        wmi_reset("root\\wmi")
        return None

def get_cpu_temps():
    if IS_WINDOWS:
        return get_cpu_temps_windows()
    return get_cpu_temps_linux()

# ─── GPU LINUX ──────────────────────────────────────────────────────────────
VENDORS_PCI = {"0x10de": "NVIDIA", "0x1002": "AMD", "0x8086": "Intel"}

def nombre_desde_lspci(linea: str, vendor: str) -> str:
    """'03:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI]
    Navi 23 [Radeon RX 6600/6600 XT/6600M] (rev c7)' -> 'AMD Radeon RX 6600/6600 XT/6600M'"""
    desc = linea.split(": ", 1)[-1]
    desc = re.sub(r"\s*\(rev \w+\)$", "", desc).strip()
    corchetes = [b for b in re.findall(r"\[([^\]]+)\]", desc) if b not in ("AMD/ATI", "AMD")]
    if corchetes and vendor:
        return f"{vendor} {corchetes[-1]}"
    return desc

def detectar_gpus_linux():
    """Detección estática (una sola vez): una entrada por GPU física."""
    gpus = []
    vistos = set()
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]*")):
        if not re.search(r"card\d+$", card):
            continue                                    # card0-HDMI-A-1, etc.
        dev = os.path.realpath(os.path.join(card, "device"))
        if dev in vistos:
            continue
        vistos.add(dev)
        vendor = VENDORS_PCI.get(leer(os.path.join(dev, "vendor"), ""), "")
        slot = os.path.basename(dev)
        nombre = leer(os.path.join(dev, "product_name"))
        if not nombre and shutil.which("lspci"):
            linea = run(["lspci", "-s", slot]).strip()
            if linea:
                nombre = nombre_desde_lspci(linea, vendor)
        gpus.append({
            "name": (nombre or f"{vendor} GPU".strip())[:50],
            "vendor": vendor,
            "card": card,
            "device": dev,
            "slot": slot.lower(),
        })

    # Sin DRM (contenedores, drivers raros): al menos NVIDIA vía nvidia-smi
    if not gpus and shutil.which("nvidia-smi"):
        for linea in run(["nvidia-smi", "--query-gpu=name,pci.bus_id", "--format=csv,noheader"]).splitlines():
            partes = [p.strip() for p in linea.split(",")]
            if len(partes) == 2:
                gpus.append({"name": partes[0][:50], "vendor": "NVIDIA", "card": None,
                             "device": None, "slot": partes[1].lower()})
    return gpus

@cache_ttl(2)
def nvidia_smi_stats():
    """Una sola llamada a nvidia-smi para todas las GPUs, indexadas por bus PCI."""
    if not shutil.which("nvidia-smi"):
        return {}
    res = {}
    salida = run(["nvidia-smi",
                  "--query-gpu=pci.bus_id,utilization.gpu,temperature.gpu,memory.used,memory.total",
                  "--format=csv,noheader,nounits"])
    for linea in salida.splitlines():
        p = [x.strip() for x in linea.split(",")]
        if len(p) != 5:
            continue
        def num(x):
            try:
                return float(x)
            except ValueError:
                return None
        # nvidia-smi usa 8 dígitos de dominio ("00000000:01:00.0"), sysfs 4
        res[p[0].lower()[-12:]] = {
            "usage": num(p[1]), "temp": num(p[2]),
            "vram_used": (num(p[3]) or 0) * 1024**2, "vram_total": (num(p[4]) or 0) * 1024**2,
        }
    return res

def hwmon_temp(base: str):
    for f in sorted(glob.glob(os.path.join(base, "hwmon", "hwmon*", "temp1_input"))):
        v = leer_int(f)
        if v is not None:
            return v / 1000
    return None

def leer_gpu_linux(gpu: dict) -> dict:
    d = {"name": gpu["name"], "usage": None, "temp": None,
         "vram_used": None, "vram_total": None, "freq": None}
    dev = gpu["device"]

    if gpu["vendor"] == "NVIDIA":
        st = nvidia_smi_stats().get(gpu["slot"][-12:])
        if st:
            d.update(st)
    elif gpu["vendor"] == "AMD" and dev:
        d["usage"] = leer_int(os.path.join(dev, "gpu_busy_percent"))
        d["vram_used"] = leer_int(os.path.join(dev, "mem_info_vram_used"))
        d["vram_total"] = leer_int(os.path.join(dev, "mem_info_vram_total"))
    elif gpu["vendor"] == "Intel" and gpu["card"]:
        # i915/xe no exponen % de uso sin root; la frecuencia actual es un buen indicador
        cur = leer_int(os.path.join(gpu["card"], "gt_act_freq_mhz"))
        mx = leer_int(os.path.join(gpu["card"], "gt_max_freq_mhz"))
        if cur is not None and mx:
            d["freq"] = (cur, mx)

    if d["temp"] is None and dev:
        d["temp"] = hwmon_temp(dev)
    return d

# ─── GPU WINDOWS ────────────────────────────────────────────────────────────
def detectar_gpus_windows():
    gpus = []
    c = wmi_conn()
    if c is not None:
        try:
            for v in c.Win32_VideoController():
                if v.Name and "Basic Display" not in v.Name and "Remote" not in v.Name:
                    gpus.append({"name": v.Name[:50]})
        except Exception:
            pass
    if not gpus and HAS_GPUTIL:
        try:
            gpus = [{"name": g.name[:50]} for g in GPUtil.getGPUs()]
        except Exception:
            pass
    if not gpus:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000")
            gpus.append({"name": winreg.QueryValueEx(key, "DriverDesc")[0][:50]})
            winreg.CloseKey(key)
        except Exception:
            pass
    return gpus

@cache_ttl(2)
def uso_gpu_contadores_windows():
    """Uso 3D de la GPU con los contadores de rendimiento nativos de Windows 10+
    (lo mismo que muestra el Administrador de tareas). No necesita LHM."""
    c = wmi_conn()
    if c is None:
        return None
    try:
        por_adaptador = {}
        for e in c.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine():
            if e.Name and "engtype_3D" in e.Name:
                luid = e.Name.split("_phys_")[0].split("luid_")[-1]
                por_adaptador[luid] = por_adaptador.get(luid, 0) + float(e.UtilizationPercentage or 0)
        return min(100.0, max(por_adaptador.values())) if por_adaptador else None
    except Exception:
        return None

def leer_gpus_windows(gpus: list) -> list:
    res = [{"name": g["name"], "usage": None, "temp": None,
            "vram_used": None, "vram_total": None, "freq": None} for g in gpus]

    # LHM / OHM: carga y temperatura por GPU ("/gpu-nvidia/0", "/atigpu/0", ...)
    lhm = {}
    for hw, tipo, nombre, valor in sensores_lhm():
        if "gpu" not in hw or valor is None:
            continue
        g = lhm.setdefault(hw, {})
        if tipo == "Load" and nombre in ("GPU Core", "D3D 3D"):
            g["usage"] = max(g.get("usage") or 0, valor)
        elif tipo == "Temperature" and nombre in ("GPU Core", "GPU Hot Spot") and "temp" not in g:
            g["temp"] = valor
        elif tipo == "SmallData" and nombre in ("GPU Memory Used", "D3D Dedicated Memory Used"):
            g["vram_used"] = valor * 1024**2
        elif tipo == "SmallData" and nombre == "GPU Memory Total":
            g["vram_total"] = valor * 1024**2
    for i, hw in enumerate(sorted(lhm)):
        if i < len(res):
            res[i].update({k: v for k, v in lhm[hw].items() if v is not None})

    if HAS_GPUTIL and res and res[0]["usage"] is None:
        try:
            g = GPUtil.getGPUs()[0]
            res[0].update({"usage": g.load * 100, "temp": g.temperature,
                           "vram_used": g.memoryUsed * 1024**2, "vram_total": g.memoryTotal * 1024**2})
        except Exception:
            pass

    if res and res[0]["usage"] is None:
        res[0]["usage"] = uso_gpu_contadores_windows()
    return res

# ─── DISCOS LINUX ───────────────────────────────────────────────────────────
DISCOS_IGNORAR = ("loop", "ram", "zram", "dm-", "md", "sr", "fd", "nbd")

def nombre_kernel(device: str):
    """'/dev/mapper/vg-root' -> 'dm-0', '/dev/nvme0n1p2' -> 'nvme0n1p2'."""
    try:
        rdev = os.stat(device).st_rdev
        return os.path.basename(os.path.realpath(f"/sys/dev/block/{os.major(rdev)}:{os.minor(rdev)}"))
    except (OSError, ValueError):
        return None

def discos_padre(nombre: str, profundidad: int = 0):
    """Resuelve partición / LVM / LUKS / RAID hasta los discos físicos."""
    base = f"/sys/class/block/{nombre}"
    if profundidad > 8 or not os.path.exists(base):
        return []
    if os.path.exists(os.path.join(base, "partition")):
        return [os.path.basename(os.path.dirname(os.path.realpath(base)))]
    try:
        esclavos = os.listdir(os.path.join(base, "slaves"))
    except OSError:
        esclavos = []
    if esclavos:
        padres = []
        for s in sorted(esclavos):
            for p in discos_padre(s, profundidad + 1):
                if p not in padres:
                    padres.append(p)
        return padres
    return [nombre]

def rutas_temp_disco(dev: str):
    """drivetemp (SATA) cuelga del dispositivo SCSI; nvme del controlador."""
    rutas = glob.glob(f"/sys/block/{dev}/device/hwmon/hwmon*/temp1_input")
    rutas += glob.glob(f"/sys/block/{dev}/device/hwmon*/temp1_input")
    m = re.match(r"nvme(\d+)", dev)
    if m and not rutas:
        ctrl = f"/sys/class/nvme/nvme{m.group(1)}"
        rutas = glob.glob(f"{ctrl}/hwmon*/temp1_input") + glob.glob(f"{ctrl}/device/hwmon/hwmon*/temp1_input")
    return sorted(rutas)[:1]

@cache_ttl(10)
def listar_discos_linux():
    """Lista estática de discos físicos y sus puntos de montaje. Se refresca
    cada 10 s (detecta USB conectados) leyendo sysfs, sin lanzar lsblk."""
    discos = {}
    try:
        nombres = sorted(os.listdir("/sys/block"))
    except OSError:
        nombres = []
    for dev in nombres:
        if dev.startswith(DISCOS_IGNORAR):
            continue
        sectores = leer_int(f"/sys/block/{dev}/size", 0)
        if not sectores:
            continue                                    # lector de tarjetas vacío, etc.
        modelo = leer(f"/sys/block/{dev}/device/model") or leer(f"/sys/block/{dev}/device/name") or ""
        fabricante = (leer(f"/sys/block/{dev}/device/vendor") or "").strip()
        # "ATA" y los ids PCI de virtio ("0x1af4") no aportan nada
        if fabricante and fabricante != "ATA" and not fabricante.startswith("0x") and not modelo.lower().startswith(fabricante.lower()):
            modelo = f"{fabricante} {modelo}"
        modelo = " ".join(modelo.split()) or dev

        ruta = os.path.realpath(f"/sys/block/{dev}")
        if "/usb" in ruta:
            tipo = "USB"
        elif dev.startswith("nvme"):
            tipo = "NVMe"
        elif dev.startswith("mmcblk"):
            tipo = "SD"
        elif dev.startswith(("vd", "xvd")):
            tipo = "VIRT"
        else:
            tipo = "HDD" if leer(f"/sys/block/{dev}/queue/rotational") == "1" else "SSD"

        discos[dev] = {
            "dev": f"/dev/{dev}",
            "model": modelo[:25],
            "tipo": tipo,
            "size": sectores * 512,                     # /sys/block/*/size siempre en sectores de 512
            "io_key": dev,
            "temp_paths": rutas_temp_disco(dev),
            "mounts": [],
        }

    # Asignar cada sistema de archivos a su disco. Se deduplica por dispositivo:
    # btrfs monta el mismo dispositivo varias veces (subvolúmenes) y antes se
    # sumaba repetido. Si un volumen LVM/RAID abarca varios discos, cuenta en el primero.
    vistos = set()
    for part in psutil.disk_partitions(all=False):
        kname = nombre_kernel(part.device)
        if not kname or kname in vistos:
            continue
        vistos.add(kname)
        for padre in discos_padre(kname):
            if padre in discos:
                discos[padre]["mounts"].append(part.mountpoint)
                break
    return list(discos.values())

def temp_disco_linux(disco):
    for p in disco["temp_paths"]:
        v = leer_int(p)
        if v is not None:
            return v / 1000
    return None

# ─── DISCOS WINDOWS ─────────────────────────────────────────────────────────
@cache_ttl(30)
def listar_discos_windows():
    discos = []
    c = wmi_conn()
    if c is not None:
        # Tipo real (SSD/HDD/NVMe/USB) desde la API de almacenamiento de Windows 8+
        tipos = {}
        st = wmi_conn("root\\Microsoft\\Windows\\Storage")
        if st is not None:
            try:
                for pd in st.MSFT_PhysicalDisk():
                    bus, media = int(pd.BusType or 0), int(pd.MediaType or 0)
                    tipos[str(pd.DeviceId)] = ("NVMe" if bus == 17 else "USB" if bus == 7
                                               else "SSD" if media == 4 else "HDD" if media == 3 else "")
            except Exception:
                pass
        try:
            for d in c.Win32_DiskDrive():
                letras = []
                try:
                    for particion in d.associators("Win32_DiskDriveToDiskPartition"):
                        for ld in particion.associators("Win32_LogicalDiskToPartition"):
                            letras.append(ld.DeviceID + "\\")
                except Exception:
                    pass
                idx = int(d.Index) if d.Index is not None else len(discos)
                discos.append({
                    "dev": f"PhysicalDrive{idx}",
                    "model": (d.Model or "Disco")[:25],
                    "tipo": tipos.get(str(idx)) or ("USB" if d.InterfaceType == "USB" else ""),
                    "size": int(d.Size) if d.Size else 0,
                    "io_key": f"PhysicalDrive{idx}",
                    "index": idx,
                    "mounts": sorted(letras),
                })
        except Exception:
            discos = []
        discos.sort(key=lambda x: x["index"])

    if not discos:
        # Sin WMI: una entrada por letra de unidad
        for part in psutil.disk_partitions():
            if "cdrom" in part.opts or not part.fstype:
                continue
            try:
                total = psutil.disk_usage(part.mountpoint).total
            except OSError:
                continue
            discos.append({"dev": part.device, "model": part.device, "tipo": "", "size": total,
                           "io_key": None, "index": None, "mounts": [part.mountpoint]})
    return discos

def temps_discos_windows():
    """{indice_disco: temp} desde LHM ('/hdd/0', '/nvme/1', '/ssd/0' ...)."""
    res = {}
    for hw, tipo, nombre, valor in sensores_lhm():
        m = re.match(r"/(hdd|ssd|nvme|storage)/(\d+)", hw)
        if m and tipo == "Temperature" and valor is not None:
            idx = int(m.group(2))
            res.setdefault(idx, valor)
    return res

# ─── RED ────────────────────────────────────────────────────────────────────
_tasa_red = Tasa()
_tasa_disco = Tasa()

@cache_ttl(10)
def detectar_red(preferida="auto"):
    """IP local e interfaz de salida (no envía paquetes: UDP connect solo
    consulta la tabla de rutas). Se cachea 10 s."""
    ip_l, iface = "N/A", None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip_l = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    try:
        addrs = psutil.net_if_addrs()
        if preferida and preferida != "auto" and preferida in addrs:
            iface = preferida
            for a in addrs[preferida]:
                if a.family == socket.AF_INET:
                    ip_l = a.address
        else:
            for name, lista in addrs.items():
                if any(a.address == ip_l for a in lista):
                    iface = name
                    break
    except Exception:
        pass
    return ip_l, iface

def get_net(preferida="auto"):
    ip_l, iface = detectar_red(preferida)
    pernic = psutil.net_io_counters(pernic=True)
    if iface and iface in pernic:
        st = pernic[iface]
        rx, tx = st.bytes_recv, st.bytes_sent
    else:
        # Sin interfaz clara: todas menos loopback (antes se sumaba 'lo')
        rx = sum(v.bytes_recv for k, v in pernic.items() if not k.lower().startswith(("lo", "loopback")))
        tx = sum(v.bytes_sent for k, v in pernic.items() if not k.lower().startswith(("lo", "loopback")))
    rx_s, tx_s = _tasa_red.calc({"net": (rx, tx)})["net"]
    return {"iface": iface or "N/A", "ip": ip_l, "rx_s": rx_s, "tx_s": tx_s,
            "rx_total": rx, "tx_total": tx}

# ─── MEMORIA ────────────────────────────────────────────────────────────────
def get_windows_commit():
    """Carga de compromiso (RAM + pagefile), como 'Confirmada' en el Administrador de tareas."""
    try:
        import ctypes
        from ctypes import wintypes

        class PERFORMANCE_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("CommitTotal", ctypes.c_size_t),
                ("CommitLimit", ctypes.c_size_t),
                ("CommitPeak", ctypes.c_size_t),
                ("PhysicalTotal", ctypes.c_size_t),
                ("PhysicalAvailable", ctypes.c_size_t),
                ("SystemCache", ctypes.c_size_t),
                ("KernelTotal", ctypes.c_size_t),
                ("KernelPaged", ctypes.c_size_t),
                ("KernelNonpaged", ctypes.c_size_t),
                ("PageSize", ctypes.c_size_t),
                ("HandleCount", wintypes.DWORD),
                ("ProcessCount", wintypes.DWORD),
                ("ThreadCount", wintypes.DWORD),
            ]

        pi = PERFORMANCE_INFORMATION()
        pi.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
        if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(pi), pi.cb):
            return None
        used = pi.CommitTotal * pi.PageSize
        total = pi.CommitLimit * pi.PageSize
        return {"total": total, "used": used, "percent": used * 100 / total if total else 0}
    except Exception:
        return None

def get_memory():
    ram = psutil.virtual_memory()
    datos = {"ram": {"total": ram.total, "used": ram.total - ram.available, "percent": ram.percent}}
    commit = get_windows_commit() if IS_WINDOWS else None
    if commit and commit["total"] > 0:
        datos["swap"] = dict(commit, name="MEM VIRT")
    else:
        sw = psutil.swap_memory()
        datos["swap"] = {"name": "SWAP", "total": sw.total, "used": sw.used, "percent": sw.percent}
    return datos

# ─── FPS ────────────────────────────────────────────────────────────────────
# Windows: PresentMon (Intel, open source) captura por ETW cada frame que
#          presenta cualquier juego DirectX/Vulkan/OpenGL. Requiere administrador.
# Linux:   MangoHud escribe registros CSV (Shift_L+F2 o autostart_log=1);
#          se lee el más reciente: en vivo si se está escribiendo, si no se
#          muestra el resumen de la última partida.
FPS_IGNORAR = {"dwm.exe", "windowsterminal.exe", "openconsole.exe", "conhost.exe",
               "explorer.exe", "searchhost.exe", "shellexperiencehost.exe",
               "startmenuexperiencehost.exe", "textinputhost.exe"}

def stats_frametimes(fts):
    """[ms por frame] -> (fps_promedio, fps_1pct_low, frametime_medio).
    1% low = FPS equivalente al percentil 99 del frametime."""
    fts = [f for f in fts if f and 0 < f < 5000]
    if not fts:
        return None, None, None
    media = sum(fts) / len(fts)
    p99 = sorted(fts)[min(len(fts) - 1, int(len(fts) * 0.99))]
    return 1000 / media, 1000 / p99, media

def pid_primer_plano():
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value
    except Exception:
        return None

def es_admin_windows():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def buscar_presentmon(ruta_cfg=""):
    if ruta_cfg:
        return ruta_cfg if os.path.isfile(ruta_cfg) else None
    for nombre in ("PresentMon.exe", "presentmon.exe"):
        r = shutil.which(nombre)
        if r:
            return r
    base = os.path.dirname(os.path.abspath(__file__))
    # Las descargas oficiales se llaman p. ej. PresentMon-2.3.0-x64.exe
    candidatos = sorted(glob.glob(os.path.join(base, "PresentMon*.exe")) +
                        glob.glob(os.path.join(base, "tools", "PresentMon*.exe")))
    candidatos = [c for c in candidatos if "arm" not in os.path.basename(c).lower()]
    return candidatos[-1] if candidatos else None

class FpsPresentMon:
    VENTANA = 10.0                                   # segundos usados para el 1% low

    def __init__(self, exe):
        self.exe = exe
        self.frames = {}                              # pid -> deque[(t, frametime_ms)]
        self.nombres = {}
        self.lock = threading.Lock()
        self.error = None
        self.proc = None
        if not es_admin_windows():
            self.error = "PresentMon necesita ejecutar SysMonitorPro como administrador"
            return
        atexit.register(self.detener)
        threading.Thread(target=self._leer, daemon=True).start()

    def detener(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def _leer(self):
        # PresentMon 2.x usa --opciones; 1.x usaba -opciones
        variantes = (["--output_stdout", "--stop_existing_session", "--session_name", "SysMonitorPro"],
                     ["-output_stdout", "-stop_existing_session", "-session_name", "SysMonitorPro"])
        ultimo = ""
        for args in variantes:
            try:
                self.proc = subprocess.Popen(
                    [self.exe] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, text=True, errors="ignore", bufsize=1,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except OSError as e:
                self.error = f"No se pudo ejecutar PresentMon: {e}"
                return
            cab = None
            for linea in self.proc.stdout:
                cols = linea.rstrip("\r\n").split(",")
                if cab is None:
                    if "Application" in cols and "ProcessID" in cols:
                        idx = {c: i for i, c in enumerate(cols)}
                        col_ft = next((idx[c] for c in ("FrameTime", "MsBetweenPresents", "msBetweenPresents")
                                       if c in idx), None)
                        if col_ft is None:
                            self.error = "Formato de PresentMon no reconocido"
                            self.detener()
                            return
                        cab = (idx["Application"], idx["ProcessID"], col_ft, len(cols))
                        self.error = None
                    elif linea.strip():
                        ultimo = linea.strip()
                    continue
                if len(cols) < cab[3]:
                    continue                          # avisos de PresentMon mezclados
                try:
                    ft = float(cols[cab[2]])
                    pid = int(cols[cab[1]])
                except ValueError:
                    continue                          # "NA" en frames descartados
                ahora = time.monotonic()
                with self.lock:
                    dq = self.frames.setdefault(pid, deque())
                    dq.append((ahora, ft))
                    while dq and ahora - dq[0][0] > self.VENTANA:
                        dq.popleft()
                    self.nombres[pid] = cols[cab[0]]
            self.proc.wait()
            if cab is not None:
                self.error = "PresentMon se detuvo"
                return
        self.error = f"PresentMon no pudo iniciar: {ultimo[:60]}" if ultimo else "PresentMon no pudo iniciar"

    def lectura(self):
        ahora = time.monotonic()
        with self.lock:
            activos = {pid: list(dq) for pid, dq in self.frames.items()
                       if dq and ahora - dq[-1][0] < 2
                       and self.nombres.get(pid, "").lower() not in FPS_IGNORAR}
            nombres = dict(self.nombres)
        if not activos:
            return {"fuente": "PresentMon", "app": None, "error": self.error}
        fg = pid_primer_plano()
        if fg in activos:
            pid = fg
        else:                                         # la terminal está delante: el que más frames da
            pid = max(activos, key=lambda p: sum(1 for t, _ in activos[p] if ahora - t <= 1))
        frames = activos[pid]
        fps, _, ft = stats_frametimes([f for t, f in frames if ahora - t <= 1])
        _, low, _ = stats_frametimes([f for _, f in frames])
        return {"fuente": "PresentMon", "app": nombres.get(pid), "pid": pid, "vivo": True,
                "fps": fps, "low1": low, "frametime": ft, "error": None}

class FpsMangoHud:
    def __init__(self, carpeta=""):
        self.carpetas = [carpeta] if carpeta else self._carpetas_auto()
        self._resumenes = {}                          # (ruta, mtime) -> lectura

    @staticmethod
    def _carpetas_auto():
        carpetas = []
        conf = os.path.expanduser("~/.config/MangoHud/MangoHud.conf")
        for linea in (leer(conf, "") or "").splitlines():
            if linea.strip().startswith("output_folder"):
                carpetas.append(os.path.expanduser(linea.split("=", 1)[1].strip()))
        carpetas += [os.path.expanduser("~/mangohud-logs"), os.path.expanduser("~")]
        return [c for c in dict.fromkeys(carpetas) if os.path.isdir(c)]

    @staticmethod
    def _cabecera(ruta):
        """Devuelve (indices, offset de datos) si el CSV es de MangoHud."""
        try:
            with open(ruta, errors="ignore") as f:
                inicio = f.read(4096)
        except OSError:
            return None
        if not inicio.startswith("os,"):              # los registros de MangoHud empiezan así
            return None
        pos = 0
        for linea in inicio.splitlines(keepends=True):
            pos += len(linea.encode())
            cols = linea.strip().split(",")
            if cols and cols[0] == "fps":
                idx = {c: i for i, c in enumerate(cols)}
                return idx, pos
        return None

    def _ultimo_registro(self):
        archivos = []
        for c in self.carpetas:
            archivos += [f for f in glob.glob(os.path.join(c, "*.csv")) if not f.endswith("_summary.csv")]
        archivos.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        for f in archivos[:5]:
            cab = self._cabecera(f)
            if cab:
                return f, cab
        return None, None

    @staticmethod
    def _filas(ruta, idx, desde, max_bytes=None):
        try:
            with open(ruta, "rb") as f:
                f.seek(0, 2)
                tam = f.tell()
                inicio = max(desde, tam - max_bytes) if max_bytes else desde
                f.seek(inicio)
                datos = f.read().decode(errors="ignore").splitlines()
        except OSError:
            return []
        if max_bytes and inicio > desde:
            datos = datos[1:]                         # primera línea posiblemente cortada
        filas = []
        i_fps, i_ft = idx.get("fps"), idx.get("frametime")
        for linea in datos:
            cols = linea.split(",")
            try:
                filas.append((float(cols[i_fps]), float(cols[i_ft]) if i_ft is not None else None))
            except (ValueError, IndexError, TypeError):
                pass
        return filas

    def lectura(self):
        ruta, cab = self._ultimo_registro()
        if not ruta:
            return {"fuente": "MangoHud", "app": None,
                    "error": "Sin registros: abre el juego con mangohud y Shift_L+F2"}
        mtime = os.path.getmtime(ruta)
        app = re.sub(r"_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$", "", os.path.splitext(os.path.basename(ruta))[0])
        vivo = time.time() - mtime < 5
        idx, desde = cab
        if vivo:
            filas = self._filas(ruta, idx, desde, max_bytes=64 * 1024)
            if not filas:
                return {"fuente": "MangoHud", "app": app, "error": None, "vivo": True,
                        "fps": None, "low1": None, "frametime": None}
            fts = [ft for _, ft in filas[-200:] if ft]
            _, low, ft_med = stats_frametimes(fts)
            return {"fuente": "MangoHud", "app": app, "vivo": True, "error": None,
                    "fps": filas[-1][0], "low1": low, "frametime": filas[-1][1] or ft_med}
        clave = (ruta, mtime)
        if clave not in self._resumenes:
            filas = self._filas(ruta, idx, desde)
            fts = [ft for _, ft in filas if ft]
            fps, low, ft_med = stats_frametimes(fts)
            if fps is None and filas:
                fps = sum(f for f, _ in filas) / len(filas)
            self._resumenes = {clave: {"fuente": "MangoHud", "app": app, "vivo": False, "error": None,
                                       "fps": fps, "low1": low, "frametime": ft_med,
                                       "hace": None}}
        res = dict(self._resumenes[clave])
        res["hace"] = time.time() - mtime
        return res

def estado_fps(cfg):
    """(disponible, motivo) para explicar en la pantalla de inicio por qué la
    sección FPS aparece o no."""
    if IS_WINDOWS:
        exe = buscar_presentmon(cfg.get("presentmon", ""))
        if not exe:
            return False, "PresentMon no encontrado (copia PresentMon-x.y.z-x64.exe en la carpeta del programa)"
        if not es_admin_windows():
            return False, "PresentMon necesita abrir SysMonitorPro como administrador"
        return True, f"PresentMon listo: {os.path.basename(exe)}"
    carpeta = os.path.expanduser(cfg.get("mangohud_logs", "") or "")
    if not carpeta and not shutil.which("mangohud"):
        return False, "MangoHud no está instalado"
    return True, "MangoHud listo: abre el juego con mangohud y graba con Shift_L+F2"

def crear_fuente_fps(cfg):
    """Solo usa lo que ya está en el equipo: si falta PresentMon (o permisos de
    administrador) o MangoHud, la sección FPS no se muestra."""
    if not estado_fps(cfg)[0]:
        return None
    if IS_WINDOWS:
        return FpsPresentMon(buscar_presentmon(cfg.get("presentmon", "")))
    return FpsMangoHud(os.path.expanduser(cfg.get("mangohud_logs", "") or ""))

# ─── RECOLECCIÓN ────────────────────────────────────────────────────────────
def get_disks():
    discos = listar_discos_windows() if IS_WINDOWS else listar_discos_linux()
    try:
        io = psutil.disk_io_counters(perdisk=True) or {}
    except Exception:
        io = {}
    tasas = _tasa_disco.calc({d["io_key"]: (io[d["io_key"]].read_bytes, io[d["io_key"]].write_bytes)
                              for d in discos if d.get("io_key") in io})
    temps_win = temps_discos_windows() if IS_WINDOWS else {}

    res = []
    for d in discos:
        used = total = 0
        for mp in d["mounts"]:
            try:
                u = psutil.disk_usage(mp)
                used += u.used
                total += u.total
            except OSError:
                pass
        r_s, w_s = tasas.get(d.get("io_key"), (None, None))
        temp = temps_win.get(d.get("index")) if IS_WINDOWS else temp_disco_linux(d)
        res.append({
            "dev": d["dev"], "model": d["model"], "tipo": d["tipo"], "size": d["size"],
            "mounts": d["mounts"], "used": used, "total": total,
            "percent": used * 100 / total if total else None,
            "read_s": r_s, "write_s": w_s, "temp": temp,
        })
    return res

def get_procs(n: int):
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
        procs.append(p.info)
    top = heapq.nlargest(n, procs, key=lambda x: x.get("cpu_percent") or 0)
    for p in top:
        user = p.get("username") or "Sistema"
        p["username"] = user.split("\\")[-1]           # "DOMINIO\\usuario" en Windows
    return top

def uptime_str(segundos: float) -> str:
    d, resto = divmod(int(segundos), 86400)
    h, resto = divmod(resto, 3600)
    m = resto // 60
    return f"{d}d {h:02d}h {m:02d}m" if d else f"{h}h {m:02d}m"

def recolectar(info: dict, cfg: dict, gpus: list, fps=None, n_procs: int = 10) -> dict:
    cpu_pcts = psutil.cpu_percent(percpu=True)
    temp_global, temps_core = get_cpu_temps()
    temps_hilo = [temps_core.get(cid) if cid is not None else None for cid in info["core_map"]]

    datos = {
        "system": {
            "hostname": info["hostname"], "os": info["os"], "kernel": info["kernel"],
            "mb": info["mb"], "uptime": time.time() - psutil.boot_time(),
            "load": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else None,
        },
        "cpu": {
            "model": info["cpu_model"],
            "percent": sum(cpu_pcts) / len(cpu_pcts) if cpu_pcts else 0.0,
            "per_core": cpu_pcts,
            "temp": temp_global,
            "temps_core": temps_hilo,
            "freq_mhz": None,
        },
        "memory": get_memory(),
    }
    try:
        f = psutil.cpu_freq()
        if f and f.current:
            datos["cpu"]["freq_mhz"] = f.current
    except Exception:
        pass
    if cfg["mostrar_gpu"]:
        datos["gpu"] = leer_gpus_windows(gpus) if IS_WINDOWS else [leer_gpu_linux(g) for g in gpus]
    if cfg["mostrar_fps"] and fps is not None:
        # Con la herramienta disponible la sección siempre se ve: con el juego
        # o con el motivo por el que todavía no hay datos.
        datos["fps"] = fps.lectura()
    if cfg["mostrar_red"]:
        datos["network"] = get_net(cfg.get("interfaz_red", "auto"))
    if cfg["mostrar_discos"]:
        datos["disks"] = get_disks()
    if cfg["mostrar_top"]:
        datos["processes"] = get_procs(n_procs)
    return datos

# ─── RENDER ─────────────────────────────────────────────────────────────────
def render(datos: dict, cols: int, intervalo: float):
    out = ["\033[H"]
    sysd, cpu = datos["system"], datos["cpu"]

    load_s = "  ".join(f"{x:.2f}" for x in sysd["load"]) if sysd["load"] else "N/A"
    out.append(f" {M}▶ SISTEMA{NC}\033[K")
    out.append(f"  {C}Host:{NC} {sysd['hostname']:<25} {C}Kernel:{NC} {sysd['kernel']}\033[K")
    out.append(f"  {C}OS:{NC} {sysd['os']:<35}\033[K")
    out.append(f"  {C}MB:{NC} {sysd['mb'][:45]}\033[K")
    out.append(f"  {C}Uptime:{NC} {uptime_str(sysd['uptime']):<20} {C}Load:{NC} {load_s}\033[K")
    out.append(sep(cols))

    # CPU
    freq = f"  {D}{cpu['freq_mhz'] / 1000:.2f} GHz{NC}" if cpu["freq_mhz"] else ""
    out.append(f" {M}▶ CPU{NC}  {D}{cpu['model'][:50]}{NC}{freq}\033[K")
    out.append(f"  {C}{'Total':<8}{NC} {barra(cpu['percent'])}{fmt_temp(cpu['temp'])}\033[K")
    for i, pct in enumerate(cpu["per_core"][:12]):
        t = cpu["temps_core"][i] if i < len(cpu["temps_core"]) else None
        out.append(f"  {C}CPU {i + 1:<4}{NC} {barra(pct)}{fmt_temp(t)}\033[K")
    if len(cpu["per_core"]) > 12:
        out.append(f"  {D}... y {len(cpu['per_core']) - 12} cores mas{NC}\033[K")
    if cpu["temp"] is None:
        ayuda = "instala/abre LibreHardwareMonitor" if IS_WINDOWS else "ejecuta: sudo sensors-detect"
        out.append(f"  {D}Temperatura no disponible ({ayuda}){NC}\033[K")
    out.append(sep(cols))

    # GPU
    if "gpu" in datos:
        if not datos["gpu"]:
            out.append(f" {M}▶ GPU{NC}  {D}No detectada{NC}\033[K")
        for g in datos["gpu"][:3]:
            out.append(f" {M}▶ GPU{NC}  {D}{g['name'][:45]}{NC}\033[K")
            if g["usage"] is not None:
                linea = barra(g["usage"])
            elif g["freq"]:
                cur, mx = g["freq"]
                linea = f"{barra(cur * 100 / mx)}  {D}{cur}/{mx} MHz{NC}"
            else:
                linea = barra_na()
            out.append(f"  {C}{'Uso':<8}{NC} {linea}{fmt_temp(g['temp'])}\033[K")
            if g["vram_total"]:
                pct = (g["vram_used"] or 0) * 100 / g["vram_total"]
                out.append(f"  {C}{'VRAM':<8}{NC} {barra(pct)}  {C}{humanize(g['vram_used'])} / {humanize(g['vram_total'])}{NC}\033[K")
        out.append(sep(cols))

    # FPS
    if "fps" in datos:
        fp = datos["fps"]
        if fp.get("app") and fp.get("fps") is not None:
            col = R if fp["fps"] < 30 else (Y if fp["fps"] < 60 else G)
            if fp.get("vivo"):
                titulo = f"{D}{fp['app'][:35]}  ({fp['fuente']}){NC}"
            else:
                mins = int((fp.get("hace") or 0) // 60)
                titulo = f"{D}última partida: {fp['app'][:28]} · hace {mins} min{NC}"
            out.append(f" {M}▶ FPS{NC}  {titulo}\033[K")
            etiqueta = "FPS" if fp.get("vivo") else "Prom."
            low = f"{fp['low1']:.0f}" if fp.get("low1") else "N/A"
            ft = f"{fp['frametime']:.1f} ms" if fp.get("frametime") else "N/A"
            out.append(f"  {C}{etiqueta:<8}{NC} {col}\033[1m{fp['fps']:>5.0f}{NC}"
                       f"   {C}1% low{NC} {low:>5}   {C}Frametime{NC} {ft}\033[K")
        elif fp.get("app"):
            out.append(f" {M}▶ FPS{NC}  {D}{fp['app'][:35]}  (esperando datos){NC}\033[K")
        else:
            motivo = fp.get("error") or f"esperando un juego ({fp['fuente']})"
            out.append(f" {M}▶ FPS{NC}  {D}{motivo[:58]}{NC}\033[K")
        out.append(sep(cols))

    # RECURSOS
    mem = datos["memory"]
    out.append(f" {M}▶ RECURSOS{NC}\033[K")
    ram = mem["ram"]
    out.append(f"  {C}{'RAM':<8}{NC} {barra(ram['percent'])}  {C}{humanize(ram['used'])} / {humanize(ram['total'])}{NC}\033[K")
    sw = mem["swap"]
    if sw["total"]:
        out.append(f"  {C}{sw['name']:<8}{NC} {barra(sw['percent'])}  {C}{humanize(sw['used'])} / {humanize(sw['total'])}{NC}\033[K")
    else:
        out.append(f"  {C}{sw['name']:<8}{NC} {D}desactivada{NC}\033[K")
    out.append(sep(cols))

    # RED
    if "network" in datos:
        n = datos["network"]
        out.append(f" {M}▶ RED{NC}  {D}{n['iface']}{NC}\033[K")
        out.append(f"  {C}IP:{NC} {n['ip']:<18} {C}↓ {humanize(n['rx_s'])}/s{NC}  {C}↑ {humanize(n['tx_s'])}/s{NC}\033[K")
        out.append(f"  {C}Total:{NC} ↓ {humanize(n['rx_total'])}  ↑ {humanize(n['tx_total'])}\033[K")
        out.append(sep(cols))

    # DISCOS FÍSICOS
    if "disks" in datos:
        out.append(f" {M}▶ DISCOS FÍSICOS{NC}\033[K")
        for d in datos["disks"]:
            tipo = f"{D}{d['tipo']:<4}{NC} " if d["tipo"] else ""
            if d["percent"] is not None:
                uso = f"{barra(d['percent'])}  {C}{humanize(d['used'])} / {humanize(d['total'])}{NC}"
            else:
                uso = f"{D}[{'·' * 12}] sin montar{NC}"
            out.append(f"  {tipo}{C}{d['model'][:20]:<20}{NC} {uso}  {D}({humanize(d['size'])}){NC}\033[K")
            if d["read_s"] is not None or d["temp"] is not None:
                io = (f"R {humanize(d['read_s'])}/s  W {humanize(d['write_s'])}/s"
                      if d["read_s"] is not None else "")
                out.append(f"       {D}{d['dev']:<16}{NC} {C}{io}{NC}{fmt_temp(d['temp'])}\033[K")
        if not datos["disks"]:
            out.append(f"  {D}No se detectaron discos{NC}\033[K")
        out.append(sep(cols))

    # PROCESOS
    if "processes" in datos:
        out.append(f" {M}▶ TOP PROCESOS{NC}  {D}(cpu%){NC}\033[K")
        out.append(f"  {C}{'PID':>7}  {'CPU%':>5}  {'MEM%':>5}  {'USER':<12}  {'NOMBRE'}{NC}\033[K")
        disponibles = shutil.get_terminal_size().lines - len(out) - 3
        for proc in datos["processes"][:max(3, min(disponibles, 10))]:
            cpu_p = proc.get("cpu_percent") or 0.0
            mem_p = proc.get("memory_percent") or 0.0
            user = proc["username"][:12]
            name = (proc.get("name") or "?")[:30]
            cpu_col = G if cpu_p < 50 else (Y if cpu_p < 80 else R)
            out.append(
                f"  {D}{proc['pid']:>7}{NC}  {cpu_col}{cpu_p:>5.1f}{NC}  "
                f"{C}{mem_p:>5.1f}{NC}  {W}{user:<12}{NC}  {name}\033[K"
            )

    out.append(f"\n  {W}q{NC} salir  {D}· refresco {intervalo:g}s{NC}\033[K")
    out.append("\033[J")

    sys.stdout.write("\n".join(out))
    sys.stdout.flush()

# ─── CONFIGURACIÓN / ARGUMENTOS ─────────────────────────────────────────────
def cargar_config(ruta: str, explicita: bool) -> dict:
    cfg = dict(CONFIG_DEFECTO)
    if os.path.exists(ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                cfg.update({k: v for k, v in json.load(f).items() if k in CONFIG_DEFECTO})
        except (OSError, ValueError) as e:
            print(f"{Y}Aviso: no se pudo leer {ruta}: {e}{NC}", file=sys.stderr)
    elif explicita:
        print(f"{R}Error: no existe el archivo de configuración {ruta}{NC}", file=sys.stderr)
        sys.exit(2)
    return cfg

def parse_args():
    ap = argparse.ArgumentParser(prog="sysmonitor", description="SysMonitorPro - Monitor de sistema avanzado")
    ap.add_argument("--json", action="store_true", help="Salida en formato JSON (una muestra, para scripts)")
    ap.add_argument("--no-gpu", action="store_true", help="Ocultar sección GPU")
    ap.add_argument("--no-disks", action="store_true", help="Ocultar sección discos")
    ap.add_argument("--no-network", action="store_true", help="Ocultar sección red")
    ap.add_argument("--no-top", action="store_true", help="Ocultar top procesos")
    ap.add_argument("--no-fps", action="store_true", help="Ocultar sección FPS")
    ap.add_argument("-i", "--interval", type=float, help="Intervalo de actualización en segundos")
    ap.add_argument("-c", "--config", help="Usar configuración específica")
    return ap.parse_args()

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()
    cfg = cargar_config(args.config or CONFIG_PATH, bool(args.config))
    if args.interval:
        cfg["intervalo"] = args.interval
    for flag, clave in (("no_gpu", "mostrar_gpu"), ("no_disks", "mostrar_discos"),
                        ("no_network", "mostrar_red"), ("no_top", "mostrar_top"),
                        ("no_fps", "mostrar_fps")):
        if getattr(args, flag):
            cfg[clave] = False
    intervalo = max(0.2, float(cfg["intervalo"]))

    system_info = get_system_info()
    gpus = []
    if cfg["mostrar_gpu"]:
        gpus = detectar_gpus_windows() if IS_WINDOWS else detectar_gpus_linux()

    fps = crear_fuente_fps(cfg) if cfg["mostrar_fps"] else None

    # Primera muestra: inicializa contadores de CPU, red y disco
    datos = recolectar(system_info, cfg, gpus, fps)

    if args.json:
        time.sleep(min(intervalo, 1.0))
        datos = recolectar(system_info, cfg, gpus, fps)
        print(json.dumps(datos, indent=2, ensure_ascii=False, default=str))
        return

    print("=" * 60)
    print(f"  {M}SysMonitorPro {NC}- Monitor de sistema avanzado")
    print("=" * 60)
    print(f"  {C}Hostname:{NC} {system_info['hostname']}")
    print(f"  {C}Sistema:{NC}  {system_info['os']}")
    print(f"  {C}Kernel:{NC}   {system_info['kernel']}")
    print(f"  {C}CPU:{NC}      {system_info['cpu_model'][:55]}")
    print(f"  {C}MB:{NC}       {system_info['mb'][:45]}")
    for g in gpus:
        print(f"  {C}GPU:{NC}      {g['name'][:45]}")
    print("-" * 60)
    if IS_WINDOWS:
        lhm = "✅ Activo" if sensores_lhm() else "❌ No detectado"
        print(f"  {C}WMI:{NC} {'✅ Disponible' if HAS_WMI else '❌ No disponible'}")
        print(f"  {C}GPUtil:{NC} {'✅ Disponible' if HAS_GPUTIL else '❌ No disponible'}")
        print(f"  {C}LibreHardwareMonitor:{NC} {lhm}")
        if not HAS_WMI:
            print(f"\n  {Y}⚠️  Para temperaturas reales:{NC}")
            print("     pip install wmi pywin32")
            print("     Ejecutar LibreHardwareMonitor")
    if cfg["mostrar_fps"]:
        ok, motivo = estado_fps(cfg)
        print(f"  {C}FPS:{NC} {'✅' if ok else '❌'} {motivo}")
    print(f"  {W}Presiona 'q' para salir{NC}")
    print("=" * 60)
    time.sleep(3)

    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()

    if not IS_WINDOWS:
        signal.signal(signal.SIGINT, salir)
        signal.signal(signal.SIGTERM, salir)
        signal.signal(signal.SIGWINCH, handle_winch)
        import select as _sel
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_cfg = termios.tcgetattr(fd) if os.isatty(fd) else None
        try:
            if old_cfg:
                tty.setcbreak(fd)
            first = True
            while True:
                if resize_event.is_set() or first:
                    resize_event.clear()
                    clear_screen()
                    first = False
                cols = shutil.get_terminal_size().columns
                render(recolectar(system_info, cfg, gpus, fps), cols, intervalo)
                ready, _, _ = _sel.select([sys.stdin], [], [], intervalo)
                if ready:
                    key = sys.stdin.read(1).lower()
                    if key in ("q", ""):
                        break
                    elif key == '\x12':                 # Ctrl+R: redibujar
                        resize_event.set()
        finally:
            if old_cfg:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_cfg)
    else:
        try:
            import msvcrt
            last_size = None
            while True:
                size = shutil.get_terminal_size()
                if size != last_size:
                    clear_screen()
                    last_size = size
                render(recolectar(system_info, cfg, gpus, fps), size.columns, intervalo)

                fin = time.monotonic() + intervalo
                while time.monotonic() < fin:
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('ascii', errors='ignore').lower()
                        if key == 'q':
                            salir()
                    time.sleep(0.05)
        except KeyboardInterrupt:
            pass

    salir()

if __name__ == "__main__":
    main()
