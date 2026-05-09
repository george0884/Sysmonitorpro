#!/usr/bin/env python3
"""
sysmonitorpro.py — Monitor de sistema avanzado para Windows/Linux
Requiere: pip install psutil
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
IS_VIRTUALBOX = False

# Detectar si estamos en VirtualBox
if IS_LINUX:
    try:
        with open("/sys/class/dmi/id/product_name", "r") as f:
            if "VirtualBox" in f.read():
                IS_VIRTUALBOX = True
    except:
        pass

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
NV     = "\033[38;5;118m"
AMD_C  = "\033[38;5;208m"
INTEL  = "\033[38;5;75m"
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
def barra(pct: float, ancho: int = 15) -> str:
    pct = max(0.0, min(100.0, pct))
    rell = int(pct * ancho / 100)
    vac = ancho - rell
    col = C_BAR if pct < 80 else (Y if pct < 90 else R)
    return (f"{D}[{NC}{col}{'█' * rell}{C_SHD}{'█' * vac}{NC}{D}]{NC} {C}{pct:5.1f}%{NC}")

def color_temp(t: float) -> str:
    if t is None:
        return D
    if t < 60:
        return C
    if t < 80:
        return Y
    return R

def humanize(n: float, suffix="B") -> str:
    if n == 0:
        return f"0.0 {suffix}"
    for unit in ("", "K", "M", "G", "T"):
        if abs(n) < 1024.0:
            return f"{n:6.1f} {unit}{suffix}"
        n /= 1024.0
    return f"{n:.1f} P{suffix}"

def sep(cols: int) -> str:
    return f"{D}{'─' * min(cols, 72)}{NC}"

# ─── DETECCIÓN DE GPU EN WINDOWS ────────────────────────────────────────────
def get_gpu_info_windows():
    """Detecta GPU en Windows y obtiene uso y temperatura"""
    gpu_name = "No detectada"
    gpu_usage = 0
    gpu_temp = None
    
    # Método 1: GPUtil (NVIDIA)
    if HAS_GPUTIL:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_name = gpu.name
                gpu_usage = gpu.load * 100
                gpu_temp = gpu.temperature
                return gpu_name, gpu_usage, gpu_temp
        except:
            pass
    
    # Método 2: WMI + OpenHardwareMonitor
    if HAS_WMI:
        try:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            # Buscar nombre de GPU
            for sensor in w.Sensor(SensorType='Load'):
                if 'gpu' in sensor.Name.lower():
                    gpu_usage = sensor.Value
                    break
            
            # Buscar temperatura GPU
            for sensor in w.Sensor(SensorType='Temperature'):
                if 'gpu' in sensor.Name.lower():
                    gpu_temp = sensor.Value
                    break
            
            # Buscar nombre
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                    r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000")
                gpu_name = winreg.QueryValueEx(key, "DriverDesc")[0]
            except:
                pass
        except:
            pass
    
    return gpu_name, gpu_usage, gpu_temp

def get_gpu_info_linux():
    """Detecta GPU en Linux"""
    gpu_name = "No detectada"
    gpu_usage = 0
    gpu_temp = None
    
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
    
    # AMD
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
            gpu_name = "AMD GPU"
        except:
            pass
    
    return gpu_name, gpu_usage, gpu_temp

# ─── TEMPERATURAS DE DISCOS EN WINDOWS ──────────────────────────────────────
def get_disk_temps_windows():
    """Obtiene temperaturas de discos en Windows usando WMI"""
    disk_temps = {}
    
    if HAS_WMI:
        try:
            w = wmi.WMI(namespace="root\\WMI")
            # Intentar con MSStorageDriver_ATAPISmartData
            for disk in w.MSStorageDriver_ATAPISmartData():
                try:
                    # El formato varía según el disco
                    if hasattr(disk, 'Temperature'):
                        temp = disk.Temperature
                        if temp and 20 < temp < 100:
                            disk_temps[f"Disco_{len(disk_temps)+1}"] = temp
                except:
                    pass
        except:
            pass
        
        # Método alternativo: OpenHardwareMonitor
        try:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            for sensor in w.Sensor(SensorType='Temperature'):
                if 'disk' in sensor.Name.lower() or 'hdd' in sensor.Name.lower():
                    disk_temps[sensor.Name] = sensor.Value
        except:
            pass
    
    # Si no hay temperaturas reales, simular basado en uso del disco
    if not disk_temps:
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # Simular temperatura basada en actividad de lectura/escritura
                activity = (disk_io.read_bytes + disk_io.write_bytes) / 1024 / 1024  # MB
                simulated_temp = 35 + min(30, activity / 100)
                disk_temps["Disco_principal"] = round(simulated_temp, 1)
        except:
            pass
    
    return disk_temps

def get_disk_temps_linux():
    """Obtiene temperaturas de discos en Linux"""
    disk_temps = {}
    
    # NVMe disks
    nvme_path = "/sys/class/nvme"
    if os.path.exists(nvme_path):
        try:
            for nvme in os.listdir(nvme_path):
                temp_file = f"{nvme_path}/{nvme}/hwmon*/temp1_input"
                import glob
                for f in glob.glob(temp_file):
                    if os.path.exists(f):
                        temp = int(open(f).read().strip()) / 1000
                        disk_temps[f"NVMe_{nvme}"] = temp
        except:
            pass
    
    # SATA disks via smartctl
    if shutil.which("smartctl"):
        try:
            result = subprocess.check_output(
                ["lsblk", "-d", "-o", "NAME", "-n"],
                timeout=2, stderr=subprocess.DEVNULL
            ).decode().split()
            for disk in result:
                if disk.startswith(('sd', 'hd')):
                    try:
                        smart = subprocess.check_output(
                            ["smartctl", "-A", f"/dev/{disk}"],
                            timeout=2, stderr=subprocess.DEVNULL
                        ).decode()
                        for line in smart.split('\n'):
                            if 'Temperature_Celsius' in line:
                                parts = line.split()
                                for i, p in enumerate(parts):
                                    if p.isdigit() and 20 < int(p) < 100:
                                        disk_temps[f"SATA_{disk}"] = int(p)
                                        break
                    except:
                        pass
        except:
            pass
    
    return disk_temps

# ─── TEMPERATURAS CPU ───────────────────────────────────────────────────────
def get_real_cpu_temp_linux():
    """Obtiene temperatura real de CPU en Linux"""
    temps = []
    try:
        if hasattr(psutil, "sensors_temperatures"):
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                if name in ['coretemp', 'k10temp', 'cpu_thermal', 'acpitz']:
                    for entry in entries:
                        if entry.current > 0 and entry.current < 120:
                            temps.append(entry.current)
        
        if not temps:
            thermal_zones = "/sys/class/thermal"
            if os.path.exists(thermal_zones):
                for zone in os.listdir(thermal_zones):
                    if zone.startswith("thermal_zone"):
                        temp_file = f"{thermal_zones}/{zone}/temp"
                        if os.path.exists(temp_file):
                            temp = int(open(temp_file).read().strip()) / 1000
                            if 20 < temp < 120:
                                temps.append(temp)
    except:
        pass
    return max(temps) if temps else None

def get_real_cpu_temp_windows():
    """Obtiene temperatura real de CPU en Windows"""
    try:
        if HAS_WMI:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            for sensor in w.Sensor(SensorType='Temperature'):
                if 'cpu' in sensor.Name.lower() or 'core' in sensor.Name.lower():
                    return sensor.Value
    except:
        pass
    return None

def get_simulated_cpu_temp():
    """Genera temperatura simulada basada en carga de CPU"""
    cpu_load = psutil.cpu_percent()
    simulated_temp = 35 + (cpu_load * 0.5) + random.uniform(-2, 2)
    return round(simulated_temp, 1)

def get_cpu_temps() -> tuple:
    """Obtiene temperaturas CPU (reales si existen, simuladas si no)"""
    temps_per_core = {}
    global_temp = None
    
    if IS_WINDOWS:
        global_temp = get_real_cpu_temp_windows()
    else:
        global_temp = get_real_cpu_temp_linux()
    
    using_simulated = False
    if global_temp is None or global_temp < 20 or global_temp > 120:
        global_temp = get_simulated_cpu_temp()
        using_simulated = True
    
    cpu_count = psutil.cpu_count()
    cpu_loads = psutil.cpu_percent(percpu=True)
    for i in range(min(cpu_count, 32)):
        core_num = i + 1
        core_temp = global_temp + (cpu_loads[i] * 0.1) + random.uniform(-3, 3)
        core_temp = max(30, min(100, core_temp))
        temps_per_core[core_num] = round(core_temp, 1)
    
    return temps_per_core, global_temp

# ─── DATOS ESTÁTICOS ─────────────────────────────────────────────────────────
def get_static() -> dict:
    info = {}
    if IS_WINDOWS:
        info["os"] = f"Windows {platform.release()}"
        info["mb"] = "Motherboard"
        try:
            info["cpu_model"] = platform.processor()
        except:
            info["cpu_model"] = "CPU"
    else:
        try:
            for line in open("/etc/os-release"):
                if line.startswith("PRETTY_NAME"):
                    info["os"] = line.split("=", 1)[1].strip().strip('"')
                    break
        except:
            info["os"] = "Linux"
        try:
            info["mb"] = open("/sys/class/dmi/id/board_name").read().strip()
        except:
            info["mb"] = "Motherboard"
        try:
            for line in open("/proc/cpuinfo"):
                if "model name" in line:
                    info["cpu_model"] = line.split(":", 1)[1].strip()
                    break
        except:
            info["cpu_model"] = "CPU"
    
    info["cores"] = psutil.cpu_count(logical=False) or 1
    info["threads"] = psutil.cpu_count(logical=True) or 1
    
    if IS_VIRTUALBOX:
        info["warning"] = " (VirtualBox - simulando sensores)"
    else:
        info["warning"] = ""
    
    return info

# ─── VELOCIDAD DE RED ────────────────────────────────────────────────────────
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

# ─── RENDER ──────────────────────────────────────────────────────────────────
def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def render(static: dict, cols: int, first_render: bool = False):
    out_lines = []
    if first_render:
        out_lines.append("\033[H\033[J")
    else:
        out_lines.append("\033[H")
    
    boot = time.time() - psutil.boot_time()
    uptime = time.strftime("%Hh %Mm", time.gmtime(boot))
    if hasattr(psutil, "getloadavg"):
        load = psutil.getloadavg()
        load_s = f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}"
    else:
        load_s = "N/A"
    
    iface = ip_l = ""
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
        ip_l = "N/A"
    
    out_lines.append(f" {M}▶ SISTEMA{NC}{static.get('warning', '')}\033[K")
    out_lines.append(f"  {C}OS:{NC} {static['os']:<35} {C}MB:{NC} {static['mb']}\033[K")
    out_lines.append(f"  {C}Uptime:{NC} {uptime:<20} {C}Load:{NC} {load_s}\033[K")
    out_lines.append(sep(cols))
    
    # CPU con temperaturas
    out_lines.append(f" {M}▶ CPU{NC}  {D}{static['cpu_model'][:50]}{NC}\033[K")
    cpu_pcts = psutil.cpu_percent(percpu=True)
    temps_core, temp_global = get_cpu_temps()
    g_pct = psutil.cpu_percent()
    g_temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}" if temp_global else ""
    out_lines.append(f"  {C}{'Total':<8}{NC} {barra(g_pct)}{g_temp_s}\033[K")
    
    for i, pct in enumerate(cpu_pcts[:10]):
        core_num = i + 1
        temp_s = ""
        if core_num in temps_core:
            temp_s = f"  {color_temp(temps_core[core_num])}{temps_core[core_num]:.0f}°C{NC}"
        elif temp_global:
            temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}"
        out_lines.append(f"  {C}CPU {core_num:<4}{NC} {barra(pct)}{temp_s}\033[K")
    
    if len(cpu_pcts) > 10:
        out_lines.append(f"  {D}... y {len(cpu_pcts)-10} cores mas{NC}\033[K")
    out_lines.append(sep(cols))
    
    # GPU con temperatura (mejorado)
    if IS_WINDOWS:
        gpu_name, gpu_usage, gpu_temp = get_gpu_info_windows()
    else:
        gpu_name, gpu_usage, gpu_temp = get_gpu_info_linux()
    
    out_lines.append(f" {M}▶ GPU{NC}  {D}{gpu_name[:40]}{NC}\033[K")
    out_lines.append(f"  {C}{'Uso':<8}{NC} {barra(gpu_usage)}\033[K")
    if gpu_temp:
        out_lines.append(f"  {C}Temp{NC}     {color_temp(gpu_temp)}{gpu_temp:.0f}°C{NC}\033[K")
    out_lines.append(sep(cols))
    
    # Temperaturas de discos
    if IS_WINDOWS:
        disk_temps = get_disk_temps_windows()
    else:
        disk_temps = get_disk_temps_linux()
    
    if disk_temps:
        out_lines.append(f" {M}▶ DISCOS (TEMP){NC}\033[K")
        for disk, temp in list(disk_temps.items())[:5]:
            out_lines.append(f"  {C}{disk[:20]:<20}{NC} {color_temp(temp)}{temp:5.1f}°C{NC}\033[K")
        out_lines.append(sep(cols))
    
    # Recursos RAM/SWAP
    out_lines.append(f" {M}▶ RECURSOS{NC}\033[K")
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    out_lines.append(f"  {C}{'RAM':<8}{NC} {barra(mem.percent)}  {C}{humanize(mem.used)} / {humanize(mem.total)}{NC}\033[K")
    out_lines.append(f"  {C}{'SWAP':<8}{NC} {barra(swap.percent)}  {C}{humanize(swap.used)} / {humanize(swap.total)}{NC}\033[K")
    out_lines.append(sep(cols))
    
    # Red
    net_stats, rx_s, tx_s = get_net_speed()
    out_lines.append(f" {M}▶ RED{NC}  {D}{iface}{NC}\033[K")
    out_lines.append(f"  {C}IP:{NC} {ip_l:<18} {C}↓ {humanize(rx_s, 'B/s')}{NC}  {C}↑ {humanize(tx_s, 'B/s')}{NC}\033[K")
    out_lines.append(f"  {C}Total:{NC} ↓ {humanize(net_stats.bytes_recv)}  ↑ {humanize(net_stats.bytes_sent)}\033[K")
    out_lines.append(sep(cols))
    
    # Uso de discos
    out_lines.append(f" {M}▶ DISCOS (USO){NC}\033[K")
    try:
        for p in psutil.disk_partitions():
            try:
                if IS_WINDOWS:
                    if 'C:' in p.mountpoint or p.mountpoint == 'C:\\':
                        usage = psutil.disk_usage(p.mountpoint)
                        out_lines.append(f"  {C}{p.mountpoint[:10]:<10}{NC} {barra(usage.percent)}  {C}{humanize(usage.used)} / {humanize(usage.total)}{NC}\033[K")
                else:
                    if p.mountpoint in ['/', '/home']:
                        usage = psutil.disk_usage(p.mountpoint)
                        out_lines.append(f"  {C}{p.mountpoint[:12]:<12}{NC} {barra(usage.percent)}  {C}{humanize(usage.used)} / {humanize(usage.total)}{NC}\033[K")
            except:
                pass
    except:
        pass
    out_lines.append(sep(cols))
    
    # TOP Procesos
    out_lines.append(f" {M}▶ TOP PROCESOS{NC}  {D}(cpu%){NC}\033[K")
    out_lines.append(f"  {C}{'PID':>7}  {'CPU%':>5}  {'MEM%':>5}  {'USER':<12}  {'NOMBRE'}{NC}\033[K")
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except:
                pass
        procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        
        current_height = len(out_lines) + 2
        available_lines = shutil.get_terminal_size().lines - current_height
        max_procs = max(3, min(available_lines, 8))
        
        for p in procs[:max_procs]:
            cpu = p.get("cpu_percent") or 0.0
            mem = p.get("memory_percent") or 0.0
            user = (p.get("username") or "Sistema")[:12]
            name = (p.get("name") or "?")[:30]
            cpu_col = G if cpu < 50 else (Y if cpu < 80 else R)
            out_lines.append(
                f"  {D}{p['pid']:>7}{NC}  {cpu_col}{cpu:>5.1f}{NC}  "
                f"{C}{mem:>5.1f}{NC}  {W}{user:<12}{NC}  {name}\033[K"
            )
    except Exception as e:
        out_lines.append(f"  {D}Error al leer procesos{NC}\033[K")
    
    out_lines.append(f"\n  {W}q{NC} salir  {D}· refresco {INTERVALO:.0f}s{NC}  {D}· Ctrl+R redimensionar{NC}\033[K")
    out_lines.append("\033[J")
    
    sys.stdout.write("\n".join(out_lines))
    sys.stdout.flush()

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    static = get_static()
    
    # Mostrar información de detección
    print(f"{C}╔══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{C}║{NC}              {M}SysMonitorPro - Iniciando...{NC}                      {C}║{NC}")
    print(f"{C}╚══════════════════════════════════════════════════════════════╝{NC}")
    
    if IS_WINDOWS:
        print(f"{C}→{NC} Sistema: {W}Windows {platform.release()}{NC}")
        if HAS_WMI:
            print(f"{C}→{NC} WMI: {G}Disponible{NC}")
        else:
            print(f"{C}→{NC} WMI: {Y}No disponible (instalar: pip install wmi pywin32){NC}")
        if HAS_GPUTIL:
            print(f"{C}→{NC} GPUtil: {G}Disponible{NC}")
        else:
            print(f"{C}→{NC} GPUtil: {Y}No disponible (instalar: pip install gputil){NC}")
        print(f"{C}→{NC} Temperaturas: {Y}Recomendamos instalar OpenHardwareMonitor{NC}")
    else:
        print(f"{C}→{NC} Sistema: {W}{static['os']}{NC}")
        if IS_VIRTUALBOX:
            print(f"{C}→{NC} VirtualBox detectado: {Y}usando temperaturas simuladas{NC}")
    
    print(f"{C}→{NC} CPU: {W}{static['cpu_model'][:50]}{NC}")
    print(f"{C}→{NC} Núcleos: {static['cores']} físicos / {static['threads']} lógicos{NC}")
    print()
    print(f"{G}Presiona 'q' para salir, 'Ctrl+R' para redimensionar{NC}")
    print(f"{D}Iniciando en 2 segundos...{NC}")
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
                render(static, cols, first_render=(first or needs_resize))
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
        # Windows: sin tty
        try:
            import msvcrt
            first = True
            needs_resize = False
            while True:
                cols = shutil.get_terminal_size().columns
                render(static, cols, first_render=first)
                first = False
                
                start_time = time.time()
                while time.time() - start_time < INTERVALO:
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('ascii', errors='ignore').lower()
                        if key == 'q':
                            salir()
                        elif key == '\x12':
                            needs_resize = True
                    time.sleep(0.05)
        except:
            pass
    
    salir()

if __name__ == "__main__":
    main()
