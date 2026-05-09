#!/usr/bin/env python3
"""
sysmonitorpro.py — Monitor de sistema avanzado para Linux con gráficos históricos,
configuración, modo JSON y detección inteligente de red.
"""
import os
import sys
import time
import signal
import shutil
import subprocess
import json
import argparse
import collections
import math
from typing import Dict, List, Tuple, Optional, Any

try:
    import psutil
except ImportError:
    print("Error: psutil no instalado. Ejecuta: pip install psutil")
    sys.exit(1)

# ─── COLORES ANSI ────────────────────────────────────────────────────────────
M      = "\033[38;5;201m"   # Magenta  (títulos)
C      = "\033[38;5;51m"    # Celeste  (etiquetas)
C_BAR  = "\033[38;5;39m"    # Azul     (barra activa)
C_SHD  = "\033[38;5;236m"   # Gris     (barra vacía)
W      = "\033[1;37m"       # Blanco
D      = "\033[2;37m"       # Gris tenue
G      = "\033[38;5;46m"    # Verde
Y      = "\033[38;5;226m"   # Amarillo
R      = "\033[38;5;196m"   # Rojo
NV     = "\033[38;5;118m"   # Verde NVIDIA
AMD_C  = "\033[38;5;208m"   # Naranja AMD
INTEL  = "\033[38;5;75m"    # Azul Intel
NC     = "\033[0m"

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "intervalo": 1.0,
    "mostrar_gpu": True,
    "mostrar_discos": True,
    "mostrar_red": True,
    "mostrar_top": True,
    "grafico_tamano": 40,
    "historial_segundos": 60,  # 60 segundos de historial
    "interfaz_red": "auto"
}

config = DEFAULT_CONFIG.copy()

# ─── HISTORIAL PARA GRÁFICOS ─────────────────────────────────────────────────
class HistoryBuffer:
    def __init__(self, maxlen: int):
        self.buffer = collections.deque(maxlen=maxlen)
    
    def append(self, value: float):
        self.buffer.append(value)
    
    def get_graph(self, width: int, height: int = 3) -> List[str]:
        """Genera gráfico ASCII de altura variable"""
        if len(self.buffer) < 2:
            return [" " * width] * height
        
        # Normalizar valores
        values = list(self.buffer)
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val - min_val > 0 else 1
        
        # Crear grid
        grid = [[" " for _ in range(width)] for _ in range(height)]
        
        # Dibujar línea
        step = max(1, len(values) // width)
        for x in range(width):
            idx = min(x * step, len(values) - 1)
            val = values[idx]
            nivel = int(((val - min_val) / range_val) * (height - 1))
            grid[height - 1 - nivel][x] = "█"
        
        return ["".join(row) for row in grid]

# Buffers globales
cpu_history = HistoryBuffer(60)
ram_history = HistoryBuffer(60)

# ─── SALIDA LIMPIA ───────────────────────────────────────────────────────────
def salir(sig=None, frame=None):
    sys.stdout.write("\033[?1049l\033[?25h")
    sys.stdout.flush()
    sys.exit(0)

signal.signal(signal.SIGINT,  salir)
signal.signal(signal.SIGTERM, salir)
signal.signal(signal.SIGWINCH, lambda s, f: None)  # Capturar redimension

# ─── BARRA DE PROGRESO ───────────────────────────────────────────────────────
def barra(pct: float, ancho: int = 15) -> str:
    pct  = max(0.0, min(100.0, pct))
    rell = int(pct * ancho / 100)
    vac  = ancho - rell
    col  = C_BAR if pct < 80 else (Y if pct < 90 else R)
    return (f"{D}[{NC}{col}{'█' * rell}{C_SHD}{'█' * vac}{NC}{D}]{NC} "
            f"{C}{pct:5.1f}%{NC}")

# ─── COLOR TEMPERATURA ───────────────────────────────────────────────────────
def color_temp(t: float) -> str:
    if t < 60: return C
    if t < 80: return Y
    return R

# ─── HUMANIZAR BYTES ─────────────────────────────────────────────────────────
def humanize(n: float, suffix="B") -> str:
    if n == 0:
        return f"0.0 {suffix}"
    for unit in ("", "K", "M", "G", "T", "P"):
        if abs(n) < 1024.0:
            return f"{n:6.1f} {unit}{suffix}"
        n /= 1024.0
    return f"{n:.1f} P{suffix}"

def sep(cols: int) -> str:
    return f"{D}{'─' * min(cols, 72)}{NC}"

# ─── DETECCIÓN DE INTERFAZ DE RED ACTIVA ─────────────────────────────────────
def get_active_interface() -> Tuple[str, str]:
    """Detecta la interfaz de red activa por defecto"""
    try:
        # Método 1: Ruta por defecto
        with open("/proc/net/route") as f:
            for line in f:
                parts = line.split()
                if len(parts) > 1 and parts[1] == "00000000":  # Default route
                    iface = parts[0]
                    return iface, get_interface_ip(iface)
    except:
        pass
    
    # Método 2: Interfaz con más tráfico
    try:
        stats = psutil.net_io_counters(pernic=True)
        if stats:
            main_iface = max(stats.items(), key=lambda x: x[1].bytes_sent + x[1].bytes_recv)[0]
            return main_iface, get_interface_ip(main_iface)
    except:
        pass
    
    # Método 3: Primera interfaz no-loopback
    for iface, addrs in psutil.net_if_addrs().items():
        if iface != "lo":
            ip = get_interface_ip(iface)
            if ip:
                return iface, ip
    
    return "N/A", "N/A"

def get_interface_ip(iface: str) -> str:
    """Obtiene IP de una interfaz específica"""
    try:
        for addr in psutil.net_if_addrs().get(iface, []):
            if addr.family == 2:  # AF_INET
                return addr.address
    except:
        pass
    return "N/A"

# ─── DATOS ESTÁTICOS ─────────────────────────────────────────────────────────
def get_static() -> dict:
    info: dict = {}
    try:
        for line in open("/etc/os-release"):
            if line.startswith("PRETTY_NAME"):
                info["os"] = line.split("=", 1)[1].strip().strip('"')
                break
    except Exception:
        info["os"] = "Linux"

    try:
        info["mb"] = open("/sys/class/dmi/id/board_name").read().strip()
    except Exception:
        info["mb"] = "Motherboard"

    try:
        for line in open("/proc/cpuinfo"):
            if "model name" in line:
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break
    except Exception:
        info["cpu_model"] = "CPU"

    info["cores"]   = psutil.cpu_count(logical=False) or 1
    info["threads"] = psutil.cpu_count(logical=True)  or 1
    
    # Detectar interfaz de red
    interface, ip = get_active_interface()
    info["interfaz_red"] = interface
    info["ip_local"] = ip
    
    info["gpu_backend"], info["gpu_data"] = detect_gpu_backend()
    return info

# ─── DETECCIÓN DE GPU (mejorada con más sensores) ────────────────────────────
def detect_gpu_backend() -> tuple:
    """
    Detecta GPU disponible en el sistema.
    Retorna (backend, datos_iniciales).
    Backends: "nvidia" | "amd_rocm" | "amd_sysfs" | "intel_sysfs" | "none"
    """
    # NVIDIA via nvidia-smi
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                timeout=2, stderr=subprocess.DEVNULL
            ).decode().strip()
            if out:
                return "nvidia", {"name": out.splitlines()[0]}
        except Exception:
            pass

    # AMD via rocm-smi
    if shutil.which("rocm-smi"):
        try:
            out = subprocess.check_output(
                ["rocm-smi", "--showproductname"],
                timeout=2, stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                if "Card series" in line or "GPU" in line:
                    name = line.split(":", 1)[-1].strip()
                    return "amd_rocm", {"name": name}
        except Exception:
            pass

    # Escanear /sys/class/drm para AMD o Intel sin driver de alto nivel
    try:
        cards = [p for p in os.listdir("/sys/class/drm") if p.startswith("card") and p[-1].isdigit()]
    except Exception:
        cards = []

    for card in sorted(cards):
        vendor_f = f"/sys/class/drm/{card}/device/vendor"
        try:
            vendor = open(vendor_f).read().strip()
        except Exception:
            continue

        if vendor == "0x1002":   # AMD
            try:
                name = open(f"/sys/class/drm/{card}/device/product_name").read().strip()
            except Exception:
                name = "AMD GPU"
            return "amd_sysfs", {"name": name, "card": card}

        if vendor == "0x8086":   # Intel
            return "intel_sysfs", {"name": "Intel GPU", "card": card}

    return "none", {}

def get_gpu_info(backend: str, init_data: dict):
    """Retorna dict con información de GPU o None si no hay."""
    if backend == "none":
        return None

    result = {
        "name":         init_data.get("name", "GPU"),
        "vendor_color": NC,
        "uso":          0.0,
        "vram_used":    0,
        "vram_total":   0,
        "temp":         None,
    }

    # ── NVIDIA ───────────────────────────────────────────────────────────────
    if backend == "nvidia":
        result["vendor_color"] = NV
        try:
            fields = "utilization.gpu,memory.used,memory.total,temperature.gpu"
            raw = subprocess.check_output(
                ["nvidia-smi", f"--query-gpu={fields}",
                 "--format=csv,noheader,nounits"],
                timeout=2, stderr=subprocess.DEVNULL
            ).decode().strip().splitlines()[0].split(",")
            result["uso"]        = float(raw[0].strip())
            result["vram_used"]  = int(raw[1].strip()) * 1024 * 1024
            result["vram_total"] = int(raw[2].strip()) * 1024 * 1024
            result["temp"]       = float(raw[3].strip())
        except Exception:
            pass
        return result

    # ── AMD via rocm-smi ─────────────────────────────────────────────────────
    if backend == "amd_rocm":
        result["vendor_color"] = AMD_C
        try:
            out = subprocess.check_output(
                ["rocm-smi", "--showuse"], timeout=2, stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                if "%" in line:
                    result["uso"] = float(line.split()[-1].replace("%", ""))
                    break

            out2 = subprocess.check_output(
                ["rocm-smi", "--showmeminfo", "vram"], timeout=2, stderr=subprocess.DEVNULL
            ).decode()
            for line in out2.splitlines():
                if "Used" in line:
                    result["vram_used"]  = int(line.split()[-1])
                if "Total" in line:
                    result["vram_total"] = int(line.split()[-1])

            out3 = subprocess.check_output(
                ["rocm-smi", "--showtemp"], timeout=2, stderr=subprocess.DEVNULL
            ).decode()
            for line in out3.splitlines():
                nums = [s for s in line.split() if s.replace(".", "").isdigit()]
                if nums:
                    result["temp"] = float(nums[0])
                    break
        except Exception:
            pass
        return result

    # ── AMD via sysfs ─────────────────────────────────────────────────────────
    if backend == "amd_sysfs":
        result["vendor_color"] = AMD_C
        card = init_data.get("card", "card0")
        base = f"/sys/class/drm/{card}/device"
        try:
            busy_f = f"{base}/gpu_busy_percent"
            if os.path.exists(busy_f):
                result["uso"] = float(open(busy_f).read().strip())

            vram_u = f"{base}/mem_info_vram_used"
            vram_t = f"{base}/mem_info_vram_total"
            if os.path.exists(vram_u):
                result["vram_used"]  = int(open(vram_u).read().strip())
                result["vram_total"] = int(open(vram_t).read().strip())

            hwmon_dir = f"{base}/hwmon"
            if os.path.isdir(hwmon_dir):
                for hw in os.listdir(hwmon_dir):
                    tf = f"{hwmon_dir}/{hw}/temp1_input"
                    if os.path.exists(tf):
                        result["temp"] = int(open(tf).read().strip()) / 1000
                        break
        except Exception:
            pass
        return result

    # ── Intel via sysfs ──────────────────────────────────────────────────────
    if backend == "intel_sysfs":
        result["vendor_color"] = INTEL
        card = init_data.get("card", "card0")
        base = f"/sys/class/drm/{card}/device"
        try:
            hwmon_dir = f"{base}/hwmon"
            if os.path.isdir(hwmon_dir):
                for hw in os.listdir(hwmon_dir):
                    tf = f"{hwmon_dir}/{hw}/temp1_input"
                    if os.path.exists(tf):
                        result["temp"] = int(open(tf).read().strip()) / 1000
                        break
            # Frecuencia actual como indicador de actividad
            freq_f = f"/sys/class/drm/{card}/gt/gt0/rps_cur_freq_mhz"
            if os.path.exists(freq_f):
                mhz = int(open(freq_f).read().strip())
                result["name"] = f"{init_data.get('name','Intel GPU')}  {mhz} MHz"
        except Exception:
            pass
        return result

    return None

# ─── TEMPERATURA CPU (mejorado) ──────────────────────────────────────────────
def get_cpu_temps() -> Tuple[Dict[int, float], Optional[float]]:
    """Obtiene temperaturas CPU con soporte para múltiples sensores"""
    temps_per_core: dict = {}
    global_temp = None
    
    # Primero intentar con psutil
    if hasattr(psutil, "sensors_temperatures"):
        try:
            sensors = psutil.sensors_temperatures()
        except Exception:
            sensors = {}
        
        # Lista ampliada de sensores comunes
        candidates = ["k10temp", "coretemp", "acpitz", "cpu_thermal", "cpu-thermal", 
                      "pch_skylake", "nvme", "iwlwifi", "ath10k_hwmon"]
        chosen = None
        for c in candidates:
            if c in sensors:
                chosen = c
                break
        if chosen is None and sensors:
            chosen = next(iter(sensors))
        if chosen:
            for e in sensors[chosen]:
                label = e.label.lower()
                if "package" in label or "tctl" in label or label == "":
                    if global_temp is None:
                        global_temp = e.current
                elif "core" in label:
                    try:
                        idx = int(''.join(filter(str.isdigit, label)))
                        temps_per_core[idx] = e.current
                    except ValueError:
                        pass
            
            if global_temp is None and sensors[chosen]:
                global_temp = sensors[chosen][0].current
    
    # Fallback: sysfs directo
    if global_temp is None:
        thermal_zones = "/sys/class/thermal"
        if os.path.exists(thermal_zones):
            try:
                for zone in os.listdir(thermal_zones):
                    if zone.startswith("thermal_zone"):
                        temp_file = f"{thermal_zones}/{zone}/temp"
                        if os.path.exists(temp_file):
                            temp = int(open(temp_file).read().strip()) / 1000
                            if global_temp is None or temp > global_temp:
                                global_temp = temp
            except:
                pass
    
    return temps_per_core, global_temp

# ─── VELOCIDAD DE RED (mejorado con interfaz específica) ─────────────────────
_prev_net      = {}
_prev_net_time = None

def get_net_speed(interface: str = None):
    """Obtiene velocidad de red para interfaz específica o todas"""
    global _prev_net, _prev_net_time
    now = time.time()
    
    if interface and interface != "N/A":
        stats = psutil.net_io_counters(pernic=True).get(interface)
        if not stats:
            stats = psutil.net_io_counters()
    else:
        stats = psutil.net_io_counters()
    
    rx_s = tx_s = 0.0
    if _prev_net_time and interface in _prev_net:
        dt = now - _prev_net_time
        if dt > 0 and _prev_net[interface]:
            rx_s = (stats.bytes_recv - _prev_net[interface].bytes_recv) / dt
            tx_s = (stats.bytes_sent - _prev_net[interface].bytes_sent) / dt
    
    _prev_net[interface] = stats
    _prev_net_time = now
    return stats, rx_s, tx_s

# ─── RENDERIZADO PRINCIPAL ───────────────────────────────────────────────────
def render(static: dict, cols: int, mode: str = "normal"):
    """Renderiza la interfaz (modo normal o JSON)"""
    if mode == "json":
        render_json(static)
        return
    
    out = ["\033[H"]
    
    # Asegurar que el buffer de historial tenga datos actuales
    cpu_pct = psutil.cpu_percent()
    mem_pct = psutil.virtual_memory().percent
    cpu_history.append(cpu_pct)
    ram_history.append(mem_pct)
    
    # ── SISTEMA ──────────────────────────────────────────────────────────────
    boot   = time.time() - psutil.boot_time()
    uptime = time.strftime("%Hh %Mm", time.gmtime(boot))
    load   = psutil.getloadavg()
    load_s = f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}"
    
    out.append(f" {M}▶ SISTEMA{NC}\033[K")
    out.append(f"  {C}OS:{NC} {static['os']:<30} {C}MB:{NC} {static['mb']}\033[K")
    out.append(f"  {C}Uptime:{NC} {uptime:<20} {C}Load:{NC} {load_s}\033[K")
    out.append(sep(cols))
    
    # ── CPU con gráfico histórico ───────────────────────────────────────────
    out.append(f" {M}▶ CPU{NC}  {D}{static['cpu_model']}{NC}\033[K")
    
    # Gráfico histórico de CPU
    graf_cpu = cpu_history.get_graph(config["grafico_tamano"], 2)
    out.append(f"  {C}Histórico CPU:{NC}")
    for line in graf_cpu:
        out.append(f"  {C_BAR}{line}{NC}")
    
    cpu_pcts  = psutil.cpu_percent(percpu=True)
    cpu_freqs = psutil.cpu_freq(percpu=True) or []
    temps_core, temp_global = get_cpu_temps()
    
    g_freq   = psutil.cpu_freq()
    g_freq_s = f"{g_freq.current/1000:.2f} GHz" if g_freq else "?.?? GHz"
    g_temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}" if temp_global else ""
    
    out.append(f"  {C}{'Total':<8}{NC} {barra(cpu_pcts[0] if cpu_pcts else cpu_pct)}  {C}{g_freq_s}{NC}{g_temp_s}\033[K")
    
    for i, pct in enumerate(cpu_pcts[:8]):  # Limitar a 8 cores para no saturar
        freq_s = f"{cpu_freqs[i].current/1000:.2f}" if i < len(cpu_freqs) and cpu_freqs[i] else "?.??"
        temp_s = f"  {color_temp(temps_core[i])}{temps_core[i]:.0f}°C{NC}" if i in temps_core else (f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}" if temp_global else "")
        
        out.append(f"  {C}Core {i:<4}{NC} {barra(pct)}  {C}{freq_s} GHz{NC}{temp_s}\033[K")
    
    if len(cpu_pcts) > 8:
        out.append(f"  {D}... y {len(cpu_pcts)-8} cores más{NC}\033[K")
    
    out.append(sep(cols))
    
    # ── GPU (si está habilitada) ────────────────────────────────────────────
    if config["mostrar_gpu"]:
        backend   = static.get("gpu_backend", "none")
        init_data = static.get("gpu_data",    {})
        gpu       = get_gpu_info(backend, init_data)
        
        if gpu:
            vc = gpu["vendor_color"]
            if backend == "nvidia":
                badge = f"{NV}[NVIDIA]{NC}"
            elif backend in ("amd_rocm", "amd_sysfs"):
                badge = f"{AMD_C}[AMD]{NC}"
            elif backend == "intel_sysfs":
                badge = f"{INTEL}[Intel]{NC}"
            else:
                badge = ""
            
            out.append(f" {M}▶ GPU{NC}  {badge}  {D}{gpu['name'][:40]}{NC}\033[K")
            out.append(f"  {C}{'Uso':<8}{NC} {barra(gpu['uso'])}\033[K")
            
            if gpu["vram_total"] > 0:
                vram_pct = gpu["vram_used"] / gpu["vram_total"] * 100
                out.append(
                    f"  {C}{'VRAM':<8}{NC} {barra(vram_pct)}  "
                    f"{C}{humanize(gpu['vram_used'])} / {humanize(gpu['vram_total'])}{NC}\033[K"
                )
            else:
                out.append(f"  {C}
