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
    info["gpu_backend"], info["gpu_data"] = "none", {}
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

# ─── TEMPERATURA CPU ─────────────────────────────────────────────────────────
def get_cpu_temps() -> tuple:
    temps_per_core = {}
    global_temp = None
    if hasattr(psutil, "sensors_temperatures"):
        try:
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                if name in ['coretemp', 'k10temp']:
                    for i, entry in enumerate(entries):
                        if 'Core' in entry.label:
                            core_num = i + 1
                            temps_per_core[core_num] = entry.current
                        if global_temp is None or entry.current > global_temp:
                            global_temp = entry.current
        except:
            pass
    return temps_per_core, global_temp

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
    load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)
    load_s = f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}"
    
    iface = ip_l = ""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_l = s.getsockname()[0]
        s.close()
    except:
        ip_l = "N/A"
    
    out_lines.append(f" {M}▶ SISTEMA{NC}\033[K")
    out_lines.append(f"  {C}OS:{NC} {static['os']:<30} {C}MB:{NC} {static['mb']}\033[K")
    out_lines.append(f"  {C}Uptime:{NC} {uptime:<20} {C}Load:{NC} {load_s}\033[K")
    out_lines.append(sep(cols))
    
    out_lines.append(f" {M}▶ CPU{NC}  {D}{static['cpu_model']}{NC}\033[K")
    cpu_pcts = psutil.cpu_percent(percpu=True)
    temps_core, temp_global = get_cpu_temps()
    g_pct = psutil.cpu_percent()
    g_temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}" if temp_global else ""
    out_lines.append(f"  {C}{'Total':<8}{NC} {barra(g_pct)}{g_temp_s}\033[K")
    
    for i, pct in enumerate(cpu_pcts[:8]):
        core_num = i + 1
        temp_s = ""
        if core_num in temps_core:
            temp_s = f"  {color_temp(temps_core[core_num])}{temps_core[core_num]:.0f}°C{NC}"
        elif temp_global:
            temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}"
        out_lines.append(f"  {C}CPU {core_num:<4}{NC} {barra(pct)}{temp_s}\033[K")
    out_lines.append(sep(cols))
    
    out_lines.append(f" {M}▶ GPU{NC}  {D}No detectada{NC}\033[K")
    out_lines.append(sep(cols))
    
    out_lines.append(f" {M}▶ RECURSOS{NC}\033[K")
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    out_lines.append(f"  {C}{'RAM':<8}{NC} {barra(mem.percent)}  {C}{humanize(mem.used)} / {humanize(mem.total)}{NC}\033[K")
    out_lines.append(f"  {C}{'SWAP':<8}{NC} {barra(swap.percent)}  {C}{humanize(swap.used)} / {humanize(swap.total)}{NC}\033[K")
    out_lines.append(sep(cols))
    
    net_stats, rx_s, tx_s = get_net_speed()
    out_lines.append(f" {M}▶ RED{NC}  {D}{iface}{NC}\033[K")
    out_lines.append(f"  {C}IP:{NC} {ip_l:<18} {C}↓ {humanize(rx_s, 'B/s')}{NC}  {C}↑ {humanize(tx_s, 'B/s')}{NC}\033[K")
    out_lines.append(sep(cols))
    
    out_lines.append(f" {M}▶ DISCOS{NC}\033[K")
    try:
        for p in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(p.mountpoint)
                out_lines.append(f"  {C}{p.mountpoint[:15]:<15}{NC} {barra(usage.percent)}  {C}{humanize(usage.used)} / {humanize(usage.total)}{NC}\033[K")
            except:
                pass
    except:
        pass
    out_lines.append(sep(cols))
    
    out_lines.append(f" {M}▶ TOP PROCESOS{NC}  {D}(cpu%){NC}\033[K")
    out_lines.append(f"  {C}{'PID':>7}  {'CPU%':>5}  {'MEM%':>5}  {'USER':<10}  {'NOMBRE'}{NC}\033[K")
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except:
                pass
        procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        for p in procs[:5]:
            cpu = p.get("cpu_percent") or 0.0
            mem = p.get("memory_percent") or 0.0
            user = (p.get("username") or "")[:10]
            name = (p.get("name") or "")[:28]
            cpu_col = G if cpu < 50 else (Y if cpu < 80 else R)
            out_lines.append(f"  {D}{p['pid']:>7}{NC}  {cpu_col}{cpu:>5.1f}{NC}  {C}{mem:>5.1f}{NC}  {W}{user:<10}{NC}  {name}\033[K")
    except:
        pass
    
    out_lines.append(f"\n  {W}q{NC} salir  {D}· refresco {INTERVALO:.0f}s{NC}\033[K")
    out_lines.append("\033[J")
    sys.stdout.write("\n".join(out_lines))
    sys.stdout.flush()

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    static = get_static()
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
        # Windows: versión simplificada sin tty
        try:
            import msvcrt
            first = True
            while True:
                cols = shutil.get_terminal_size().columns
                render(static, cols, first_render=first)
                first = False
                time.sleep(INTERVALO)
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('ascii').lower()
                    if key == 'q':
                        break
        except:
            pass
    
    salir()

if __name__ == "__main__":
    main()
