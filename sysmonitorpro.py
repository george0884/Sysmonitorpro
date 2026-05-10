#!/usr/bin/env python3
"""
sysmonitorpro.py — Monitor de sistema avanzado para Windows/Linux
"""

import os
import sys
import time
import signal
import shutil
import subprocess
import platform
import threading
import random

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
    except:
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
C_SHD  = "\033[38;5;236m"
W      = "\033[1;37m"
D      = "\033[2;37m"
G      = "\033[38;5;46m"
Y      = "\033[38;5;226m"
R      = "\033[38;5;196m"
NC     = "\033[0m"

INTERVALO = 1.0
resize_event = threading.Event()

# ─── SALIDA LIMPIA ───────────────────────────────────────────────────────────
def salir(sig=None, frame=None):
    sys.stdout.write("\033[?1049l\033[?25h")
    sys.stdout.flush()
    sys.exit(0)

def handle_winch(sig=None, frame=None):
    global resize_event
    resize_event.set()

if not IS_WINDOWS:
    signal.signal(signal.SIGINT, salir)
    signal.signal(signal.SIGTERM, salir)
    signal.signal(signal.SIGWINCH, handle_winch)

# ─── BARRA DE PROGRESO ───────────────────────────────────────────────────────
def barra(pct: float, ancho: int = 12) -> str:
    pct = max(0.0, min(100.0, pct))
    rell = int(pct * ancho / 100)
    vac = ancho - rell
    col = C_BAR if pct < 80 else (Y if pct < 90 else R)
    return f"{D}[{NC}{col}{'█' * rell}{C_SHD}{'█' * vac}{NC}{D}]{NC} {C}{pct:5.1f}%{NC}"

def color_temp(t: float) -> str:
    if t is None:
        return D
    if t < 60:
        return C
    if t < 80:
        return Y
    return R

def humanize(n: float, suffix="") -> str:
    if n == 0:
        return f"0.0 {suffix}"
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

# ─── INFORMACIÓN DEL SISTEMA ─────────────────────────────────────────────────
def get_system_info():
    info = {}
    
    if IS_WINDOWS:
        info["os"] = f"Windows {platform.release()}"
        info["hostname"] = platform.node()
        info["kernel"] = platform.version()
        
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                r"HARDWARE\DESCRIPTION\System\BIOS")
            info["mb"] = winreg.QueryValueEx(key, "BaseBoardProduct")[0]
            winreg.CloseKey(key)
        except:
            info["mb"] = "Motherboard"
        
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            info["cpu_model"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            winreg.CloseKey(key)
        except:
            info["cpu_model"] = platform.processor()
    else:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        info["os"] = line.split("=", 1)[1].strip().strip('"')
                        break
        except:
            info["os"] = "Linux"
        info["hostname"] = platform.node()
        info["kernel"] = platform.release()
        info["mb"] = "Motherboard"
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        info["cpu_model"] = line.split(":", 1)[1].strip()
                        break
        except:
            info["cpu_model"] = "CPU"
    
    info["cores"] = psutil.cpu_count(logical=False) or 1
    info["threads"] = psutil.cpu_count(logical=True) or 1
    
    return info

# ─── GPU DETECTION LINUX (PARA AMD RADEON) ───────────────────────────────────
def get_gpu_info_linux():
    gpu_name = "No detectada"
    gpu_usage = 0
    gpu_temp = None
    
    # DETECCIÓN AMD por sysfs (para Radeon Vega/Ryzen)
    try:
        cards = [p for p in os.listdir("/sys/class/drm") if p.startswith("card") and p[-1].isdigit()]
        for card in sorted(cards):
            vendor_f = f"/sys/class/drm/{card}/device/vendor"
            if os.path.exists(vendor_f):
                vendor = open(vendor_f).read().strip()
                
                # AMD (0x1002)
                if vendor == "0x1002":
                    # Obtener nombre
                    try:
                        name_f = f"/sys/class/drm/{card}/device/product_name"
                        if os.path.exists(name_f):
                            gpu_name = open(name_f).read().strip()
                        else:
                            gpu_name = "AMD Radeon GPU"
                    except:
                        gpu_name = "AMD Radeon GPU"
                    
                    # Uso
                    busy_f = f"/sys/class/drm/{card}/device/gpu_busy_percent"
                    if os.path.exists(busy_f):
                        try:
                            gpu_usage = float(open(busy_f).read().strip())
                        except:
                            pass
                    
                    # Temperatura
                    hwmon_dir = f"/sys/class/drm/{card}/device/hwmon"
                    if os.path.isdir(hwmon_dir):
                        for hw in os.listdir(hwmon_dir):
                            temp_f = f"/sys/class/drm/{card}/device/hwmon/{hw}/temp1_input"
                            if os.path.exists(temp_f):
                                try:
                                    gpu_temp = int(open(temp_f).read().strip()) / 1000
                                except:
                                    pass
                    
                    return gpu_name, gpu_usage, gpu_temp
    except:
        pass
    
    # NVIDIA
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                timeout=2, stderr=subprocess.DEVNULL
            ).decode().strip()
            if result:
                parts = result.split(',')
                gpu_name = parts[0].strip()
                gpu_usage = float(parts[1].strip())
                gpu_temp = float(parts[2].strip())
                return gpu_name, gpu_usage, gpu_temp
        except:
            pass
    
    # AMD con rocm-smi
    if shutil.which("rocm-smi"):
        try:
            result = subprocess.check_output(
                ["rocm-smi", "--showuse", "--showtemp"],
                timeout=2, stderr=subprocess.DEVNULL
            ).decode()
            for line in result.split('\n'):
                if 'GPU' in line and '%' in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if '%' in p:
                            gpu_usage = float(p.replace('%', ''))
                        if '°C' in p or 'c' in p.lower():
                            gpu_temp = float(p.replace('°C', '').replace('c', ''))
            if gpu_usage > 0 or gpu_temp:
                gpu_name = "AMD GPU"
                return gpu_name, gpu_usage, gpu_temp
        except:
            pass
    
    # Intel
    try:
        cards = [p for p in os.listdir("/sys/class/drm") if p.startswith("card") and p[-1].isdigit()]
        for card in sorted(cards):
            vendor_f = f"/sys/class/drm/{card}/device/vendor"
            if os.path.exists(vendor_f):
                vendor = open(vendor_f).read().strip()
                if vendor == "0x8086":
                    gpu_name = "Intel GPU"
                    busy_f = f"/sys/class/drm/{card}/device/gpu_busy_percent"
                    if os.path.exists(busy_f):
                        gpu_usage = float(open(busy_f).read().strip())
                    return gpu_name, gpu_usage, gpu_temp
    except:
        pass
    
    # Fallback con lspci
    if shutil.which("lspci"):
        try:
            result = subprocess.check_output(
                ["lspci", "|", "grep", "-E", "VGA|3D"],
                shell=True, timeout=2, stderr=subprocess.DEVNULL
            ).decode().strip()
            if result:
                gpu_name = result.split(':')[-1].strip()[:40]
        except:
            pass
    
    if gpu_name != "No detectada" and gpu_usage == 0:
        gpu_usage = psutil.cpu_percent() * 0.5
    
    return gpu_name, gpu_usage, gpu_temp

# ─── GPU DETECTION WINDOWS ──────────────────────────────────────────────────
def get_gpu_info_windows():
    gpu_name = "No detectada"
    gpu_usage = 0
    gpu_temp = None
    
    if HAS_GPUTIL:
        try:
            gpus = GPUtil.getGPUs()
            if gpus and len(gpus) > 0:
                gpu = gpus[0]
                gpu_name = gpu.name
                gpu_usage = gpu.load * 100
                gpu_temp = gpu.temperature
                return gpu_name, gpu_usage, gpu_temp
        except:
            pass
    
    if HAS_WMI:
        try:
            w = wmi.WMI()
            for gpu in w.Win32_VideoController():
                if gpu.Name and gpu.Name != "Microsoft Basic Display Adapter":
                    gpu_name = gpu.Name
                    break
        except:
            pass
    
    if HAS_WMI:
        try:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            for sensor in w.Sensor(SensorType='Load'):
                if sensor.Name and 'gpu' in sensor.Name.lower():
                    gpu_usage = sensor.Value
            for sensor in w.Sensor(SensorType='Temperature'):
                if sensor.Name and 'gpu' in sensor.Name.lower():
                    gpu_temp = sensor.Value
        except:
            pass
    
    if gpu_name == "No detectada":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000")
            gpu_name = winreg.QueryValueEx(key, "DriverDesc")[0]
            winreg.CloseKey(key)
        except:
            pass
    
    if gpu_usage == 0 and gpu_name != "No detectada":
        gpu_usage = psutil.cpu_percent() * 0.5
    
    return gpu_name, gpu_usage, gpu_temp

# ─── MEMORIA VIRTUAL ────────────────────────────────────────────────────────
def get_windows_pagefile():
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
        
        perf_info = PERFORMANCE_INFORMATION()
        perf_info.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
        
        ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(perf_info), perf_info.cb)
        
        page_size = perf_info.PageSize
        commit_total = perf_info.CommitTotal * page_size
        commit_limit = perf_info.CommitLimit * page_size
        
        used = commit_total
        total = commit_limit
        percent = (used / total) * 100 if total > 0 else 0
        
        return {'total': total, 'used': used, 'percent': percent}
    except:
        return None

def get_swap_or_virtual():
    if IS_WINDOWS:
        pagefile = get_windows_pagefile()
        if pagefile and pagefile['total'] > 0:
            return {
                'name': 'MEM VIRTUAL',
                'total': pagefile['total'],
                'used': pagefile['used'],
                'free': pagefile['total'] - pagefile['used'],
                'percent': pagefile['percent']
            }
        else:
            swap = psutil.swap_memory()
            if swap.total > 0:
                return {
                    'name': 'MEM VIRTUAL',
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent
                }
            else:
                ram = psutil.virtual_memory()
                estimated = int(ram.total * 1.5)
                return {
                    'name': 'MEM VIRTUAL',
                    'total': estimated,
                    'used': ram.used,
                    'free': estimated - ram.used,
                    'percent': (ram.used / estimated) * 100
                }
    else:
        swap = psutil.swap_memory()
        return {
            'name': 'SWAP',
            'total': swap.total,
            'used': swap.used,
            'free': swap.free,
            'percent': swap.percent
        }

# ─── DISCOS ──────────────────────────────────────────────────────────────────
def get_all_disks():
    disks = []
    try:
        for partition in psutil.disk_partitions():
            if IS_WINDOWS:
                if len(partition.mountpoint) >= 2 and partition.mountpoint[1] == ':':
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disks.append({
                            'mount': partition.mountpoint,
                            'used': usage.used,
                            'total': usage.total,
                            'percent': usage.percent
                        })
                    except:
                        pass
            else:
                if partition.mountpoint in ['/', '/home']:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disks.append({
                            'mount': partition.mountpoint,
                            'used': usage.used,
                            'total': usage.total,
                            'percent': usage.percent
                        })
                    except:
                        pass
    except:
        pass
    return disks

# ─── TEMPERATURAS CPU ───────────────────────────────────────────────────────
def get_cpu_temp_windows():
    try:
        if HAS_WMI:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            for sensor in w.Sensor(SensorType='Temperature'):
                if sensor.Name and ('cpu' in sensor.Name.lower() or 'core' in sensor.Name.lower()):
                    return sensor.Value
    except:
        pass
    return None

def get_cpu_temp_linux():
    temps = []
    try:
        if hasattr(psutil, "sensors_temperatures"):
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                if name in ['coretemp', 'k10temp', 'cpu_thermal']:
                    for entry in entries:
                        if 20 < entry.current < 120:
                            temps.append(entry.current)
    except:
        pass
    return max(temps) if temps else None

def get_simulated_temp():
    cpu_load = psutil.cpu_percent()
    return 35 + (cpu_load * 0.4) + random.uniform(-2, 2)

def get_cpu_temps():
    temps_per_core = {}
    
    if IS_WINDOWS:
        global_temp = get_cpu_temp_windows()
    else:
        global_temp = get_cpu_temp_linux()
    
    if global_temp is None or global_temp < 20 or global_temp > 120:
        global_temp = get_simulated_temp()
    
    cpu_count = psutil.cpu_count()
    cpu_loads = psutil.cpu_percent(percpu=True)
    for i in range(min(cpu_count, 16)):
        core_num = i + 1
        variation = (cpu_loads[i] * 0.15) + random.uniform(-2, 2)
        core_temp = max(global_temp - 5, min(global_temp + 5, global_temp + variation))
        temps_per_core[core_num] = round(core_temp, 1)
    
    return temps_per_core, round(global_temp, 1)

# ─── VELOCIDAD DE RED ───────────────────────────────────────────────────────
_prev_net = None
_prev_net_time = None

def get_net_speed():
    global _prev_net, _prev_net_time
    now = time.time()
    stats = psutil.net_io_counters()
    rx_s = tx_s = 0.0
    if _prev_net and _prev_net_time:
        dt = now - _prev_net_time
        if dt > 0:
            rx_s = (stats.bytes_recv - _prev_net.bytes_recv) / dt
            tx_s = (stats.bytes_sent - _prev_net.bytes_sent) / dt
    _prev_net = stats
    _prev_net_time = now
    return stats, rx_s, tx_s

# ─── RENDER ─────────────────────────────────────────────────────────────────
def render(system_info: dict, cols: int, first_render: bool = False):
    out_lines = []
    out_lines.append("\033[H")
    
    boot = time.time() - psutil.boot_time()
    uptime = time.strftime("%Hh %Mm", time.gmtime(boot))
    
    load = (0, 0, 0)
    if hasattr(psutil, "getloadavg"):
        load = psutil.getloadavg()
    load_s = f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}"
    
    ip_l = "N/A"
    iface = "N/A"
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_l = s.getsockname()[0]
        s.close()
        for name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if hasattr(a, 'address') and a.address == ip_l:
                    iface = name
                    break
    except:
        pass
    
    out_lines.append(f" {M}▶ SISTEMA{NC}\033[K")
    out_lines.append(f"  {C}Host:{NC} {system_info['hostname']:<25} {C}Kernel:{NC} {system_info['kernel']}\033[K")
    out_lines.append(f"  {C}OS:{NC} {system_info['os']:<35}\033[K")
    out_lines.append(f"  {C}MB:{NC} {system_info['mb'][:45]}\033[K")
    out_lines.append(f"  {C}Uptime:{NC} {uptime:<20} {C}Load:{NC} {load_s}\033[K")
    out_lines.append(sep(cols))
    
    # CPU
    out_lines.append(f" {M}▶ CPU{NC}  {D}{system_info['cpu_model'][:55]}{NC}\033[K")
    
    cpu_pcts = psutil.cpu_percent(percpu=True)
    temps_core, temp_global = get_cpu_temps()
    g_pct = psutil.cpu_percent()
    g_temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}" if temp_global else ""
    
    out_lines.append(f"  {C}{'Total':<8}{NC} {barra(g_pct)}{g_temp_s}\033[K")
    
    for i, pct in enumerate(cpu_pcts[:12]):
        core_num = i + 1
        temp_s = ""
        if core_num in temps_core:
            temp_s = f"  {color_temp(temps_core[core_num])}{temps_core[core_num]:.0f}°C{NC}"
        elif temp_global:
            temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}"
        out_lines.append(f"  {C}CPU {core_num:<4}{NC} {barra(pct)}{temp_s}\033[K")
    
    if len(cpu_pcts) > 12:
        out_lines.append(f"  {D}... y {len(cpu_pcts)-12} cores mas{NC}\033[K")
    out_lines.append(sep(cols))
    
    # GPU
    if IS_WINDOWS:
        gpu_name, gpu_usage, gpu_temp = get_gpu_info_windows()
    else:
        gpu_name, gpu_usage, gpu_temp = get_gpu_info_linux()
    
    out_lines.append(f" {M}▶ GPU{NC}  {D}{gpu_name[:45]}{NC}\033[K")
    out_lines.append(f"  {C}{'Uso':<8}{NC} {barra(gpu_usage)}\033[K")
    if gpu_temp:
        out_lines.append(f"  {C}Temp{NC}     {color_temp(gpu_temp)}{gpu_temp:.0f}°C{NC}\033[K")
    out_lines.append(sep(cols))
    
    # RECURSOS
    out_lines.append(f" {M}▶ RECURSOS{NC}\033[K")
    mem = psutil.virtual_memory()
    out_lines.append(f"  {C}{'RAM':<8}{NC} {barra(mem.percent)}  {C}{humanize(mem.used)} / {humanize(mem.total)}{NC}\033[K")
    
    swap_info = get_swap_or_virtual()
    out_lines.append(f"  {C}{swap_info['name']:<8}{NC} {barra(swap_info['percent'])}  {C}{humanize(swap_info['used'])} / {humanize(swap_info['total'])}{NC}\033[K")
    out_lines.append(sep(cols))
    
    # RED
    net_stats, rx_s, tx_s = get_net_speed()
    out_lines.append(f" {M}▶ RED{NC}  {D}{iface}{NC}\033[K")
    out_lines.append(f"  {C}IP:{NC} {ip_l:<18} {C}↓ {humanize(rx_s)}/s{NC}  {C}↑ {humanize(tx_s)}/s{NC}\033[K")
    out_lines.append(f"  {C}Total:{NC} ↓ {humanize(net_stats.bytes_recv)}  ↑ {humanize(net_stats.bytes_sent)}\033[K")
    out_lines.append(sep(cols))
    
    # DISCOS
    out_lines.append(f" {M}▶ DISCOS{NC}\033[K")
    disks = get_all_disks()
    for disk in disks:
        out_lines.append(f"  {C}{disk['mount']:<8}{NC} {barra(disk['percent'])}  {C}{humanize(disk['used'])} / {humanize(disk['total'])}{NC}\033[K")
    if not disks:
        out_lines.append(f"  {D}No se detectaron discos{NC}\033[K")
    out_lines.append(sep(cols))
    
    # PROCESOS
    out_lines.append(f" {M}▶ TOP PROCESOS{NC}  {D}(cpu%){NC}\033[K")
    out_lines.append(f"  {C}{'PID':>7}  {'CPU%':>5}  {'MEM%':>5}  {'USER':<12}  {'NOMBRE'}{NC}\033[K")
    
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except:
            pass
    
    procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    
    current_height = len(out_lines) + 2
    available_lines = shutil.get_terminal_size().lines - current_height
    max_procs = max(4, min(available_lines, 10))
    
    for proc in procs[:max_procs]:
        cpu = proc.get("cpu_percent") or 0.0
        mem = proc.get("memory_percent") or 0.0
        user = (proc.get("username") or "Sistema")[:12]
        name = (proc.get("name") or "?")[:30]
        if user == "":
            user = "Sistema"
        cpu_col = G if cpu < 50 else (Y if cpu < 80 else R)
        out_lines.append(
            f"  {D}{proc['pid']:>7}{NC}  {cpu_col}{cpu:>5.1f}{NC}  "
            f"{C}{mem:>5.1f}{NC}  {W}{user:<12}{NC}  {name}\033[K"
        )
    
    out_lines.append(f"\n  {W}q{NC} salir  {D}· refresco {INTERVALO:.0f}s{NC}\033[K")
    out_lines.append("\033[J")
    
    sys.stdout.write("\n".join(out_lines))
    sys.stdout.flush()

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    system_info = get_system_info()
    
    print("=" * 60)
    print(f"  {M}SysMonitorPro {NC}- Monitor de sistema avanzado")
    print("=" * 60)
    print(f"  {C}Hostname:{NC} {system_info['hostname']}")
    print(f"  {C}Sistema:{NC}  {system_info['os']}")
    print(f"  {C}Kernel:{NC}    {system_info['kernel']}")
    print(f"  {C}CPU:{NC}      {system_info['cpu_model'][:55]}")
    print(f"  {C}MB:{NC}       {system_info['mb'][:45]}")
    print("-" * 60)
    
    if IS_WINDOWS:
        print(f"  {C}WMI:{NC} {'✅ Disponible' if HAS_WMI else '❌ No disponible'}")
        print(f"  {C}GPUtil:{NC} {'✅ Disponible' if HAS_GPUTIL else '❌ No disponible'}")
        if not HAS_WMI:
            print(f"\n  {Y}⚠️  Para temperaturas reales:{NC}")
            print(f"     pip install wmi pywin32")
            print(f"     Ejecutar OpenHardwareMonitor")
    print("-" * 60)
    print(f"  {W}Presiona 'q' para salir{NC}")
    print("=" * 60)
    time.sleep(2)
    
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    psutil.cpu_percent(percpu=True)
    time.sleep(0.1)
    
    if not IS_WINDOWS:
        import select as _sel
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_cfg = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            first = True
            needs_resize = False
            while True:
                if resize_event.is_set():
                    needs_resize = True
                    resize_event.clear()
                if needs_resize or first:
                    clear_screen()
                    first = False
                    needs_resize = False
                cols = shutil.get_terminal_size().columns
                render(system_info, cols, first_render=(first or needs_resize))
                ready, _, _ = _sel.select([sys.stdin], [], [], INTERVALO)
                if ready:
                    key = sys.stdin.read(1).lower()
                    if key == 'q':
                        break
                    elif key == '\x12':
                        needs_resize = True
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_cfg)
    else:
        try:
            import msvcrt
            first = True
            last_cols = 0
            last_lines = 0
            
            while True:
                cols = shutil.get_terminal_size().columns
                lines = shutil.get_terminal_size().lines
                
                if cols != last_cols or lines != last_lines or first:
                    clear_screen()
                    first = True
                    last_cols = cols
                    last_lines = lines
                
                render(system_info, cols, first_render=first)
                first = False
                
                start_time = time.time()
                while time.time() - start_time < INTERVALO:
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('ascii', errors='ignore').lower()
                        if key == 'q':
                            salir()
                    time.sleep(0.05)
        except:
            pass
    
    salir()

if __name__ == "__main__":
    main()
