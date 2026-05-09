#!/usr/bin/env python3
"""
sysmonitorpro.py — Monitor de sistema avanzado para Linux
Requiere: pip install psutil
Opcional: pip install gputil          (NVIDIA vía nvidia-smi)
          pip install pyamdgpuinfo     (AMD vía ROCm)
"""

import os, sys, time, signal, shutil, subprocess
import psutil

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

INTERVALO = 1.0

# ─── SALIDA LIMPIA ───────────────────────────────────────────────────────────
def salir(sig=None, frame=None):
    sys.stdout.write("\033[?1049l\033[?25h")
    sys.stdout.flush()
    sys.exit(0)

signal.signal(signal.SIGINT,  salir)
signal.signal(signal.SIGTERM, salir)

# ─── BARRA DE PROGRESO (unificada para CPU cores, GPU, RAM, SWAP, disco) ─────
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
    for unit in ("", "K", "M", "G", "T"):
        if abs(n) < 1024.0:
            return f"{n:6.1f} {unit}{suffix}"
        n /= 1024.0
    return f"{n:.1f} P{suffix}"

def sep(cols: int) -> str:
    return f"{D}{'─' * min(cols, 72)}{NC}"

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
    info["gpu_backend"], info["gpu_data"] = detect_gpu_backend()
    return info

# ─── DETECCIÓN DE GPU ────────────────────────────────────────────────────────
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
    """
    Retorna dict con: name, vendor_color, uso, vram_used, vram_total, temp
    o None si no hay GPU.
    """
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

# ─── TEMPERATURA CPU ─────────────────────────────────────────────────────────
def get_cpu_temps() -> tuple:
    temps_per_core: dict = {}
    global_temp = None
    if not hasattr(psutil, "sensors_temperatures"):
        return temps_per_core, global_temp
    try:
        sensors = psutil.sensors_temperatures()
    except Exception:
        return temps_per_core, global_temp

    candidates = ["k10temp", "coretemp", "acpitz", "cpu_thermal", "cpu-thermal"]
    chosen = None
    for c in candidates:
        if c in sensors:
            chosen = c
            break
    if chosen is None and sensors:
        chosen = next(iter(sensors))
    if not chosen:
        return temps_per_core, global_temp

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
    return temps_per_core, global_temp

# ─── VELOCIDAD DE RED ────────────────────────────────────────────────────────
_prev_net      = None
_prev_net_time = None

def get_net_speed():
    global _prev_net, _prev_net_time
    now   = time.time()
    stats = psutil.net_io_counters()
    rx_s = tx_s = 0.0
    if _prev_net and _prev_net_time:
        dt = now - _prev_net_time
        if dt > 0:
            rx_s = (stats.bytes_recv - _prev_net.bytes_recv) / dt
            tx_s = (stats.bytes_sent - _prev_net.bytes_sent) / dt
    _prev_net      = stats
    _prev_net_time = now
    return stats, rx_s, tx_s

# ─── RENDER ──────────────────────────────────────────────────────────────────
def render(static: dict, cols: int):
    out = ["\033[H"]

    # ── SISTEMA ──────────────────────────────────────────────────────────────
    boot   = time.time() - psutil.boot_time()
    uptime = time.strftime("%Hh %Mm", time.gmtime(boot))
    load   = psutil.getloadavg()
    load_s = f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}"

    iface = ip_l = ""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_l = s.getsockname()[0]
        s.close()
        for name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.address == ip_l:
                    iface = name
                    break
    except Exception:
        ip_l = "N/A"

    out.append(f" {M}▶ SISTEMA{NC}\033[K")
    out.append(f"  {C}OS:{NC} {static['os']:<30} {C}MB:{NC} {static['mb']}\033[K")
    out.append(f"  {C}Uptime:{NC} {uptime:<20} {C}Load:{NC} {load_s}\033[K")
    out.append(sep(cols))

    # ── CPU — todos los cores con barra idéntica a RAM ────────────────────────
    out.append(f" {M}▶ CPU{NC}  {D}{static['cpu_model']}{NC}\033[K")

    cpu_pcts  = psutil.cpu_percent(percpu=True)
    cpu_freqs = psutil.cpu_freq(percpu=True) or []
    temps_core, temp_global = get_cpu_temps()

    g_pct    = psutil.cpu_percent()
    g_freq   = psutil.cpu_freq()
    g_freq_s = f"{g_freq.current/1000:.2f} GHz" if g_freq else "?.?? GHz"
    g_temp_s = ""
    if temp_global is not None:
        ct = color_temp(temp_global)
        g_temp_s = f"  {ct}{temp_global:.0f}°C{NC}"

    out.append(f"  {C}{'Total':<8}{NC} {barra(g_pct)}  {C}{g_freq_s}{NC}{g_temp_s}\033[K")

    for i, pct in enumerate(cpu_pcts):
        freq_s = "?.??"
        if i < len(cpu_freqs) and cpu_freqs[i]:
            freq_s = f"{cpu_freqs[i].current/1000:.2f}"
        if i in temps_core:
            ct     = color_temp(temps_core[i])
            temp_s = f"  {ct}{temps_core[i]:.0f}°C{NC}"
        elif temp_global is not None:
            ct     = color_temp(temp_global)
            temp_s = f"  {ct}{temp_global:.0f}°C{NC}"
        else:
            temp_s = ""

        out.append(f"  {C}Core {i:<4}{NC} {barra(pct)}  {C}{freq_s} GHz{NC}{temp_s}\033[K")

    out.append(sep(cols))

    # ── GPU ───────────────────────────────────────────────────────────────────
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
            out.append(f"  {C}VRAM{NC}     {D}no disponible{NC}\033[K")

        if gpu["temp"] is not None:
            ct = color_temp(gpu["temp"])
            out.append(f"  {C}Temp{NC}     {ct}{gpu['temp']:.0f}°C{NC}\033[K")
    else:
        out.append(f" {M}▶ GPU{NC}  {D}No detectada o sin driver{NC}\033[K")

    out.append(sep(cols))

    # ── RECURSOS ─────────────────────────────────────────────────────────────
    out.append(f" {M}▶ RECURSOS{NC}\033[K")
    mem  = psutil.virtual_memory()
    swap = psutil.swap_memory()
    out.append(f"  {C}{'RAM':<8}{NC} {barra(mem.percent)}  "
               f"{C}{humanize(mem.used)} / {humanize(mem.total)}{NC}\033[K")
    out.append(f"  {C}{'SWAP':<8}{NC} {barra(swap.percent)}  "
               f"{C}{humanize(swap.used)} / {humanize(swap.total)}{NC}\033[K")
    out.append(sep(cols))

    # ── RED ───────────────────────────────────────────────────────────────────
    net_stats, rx_s, tx_s = get_net_speed()
    out.append(f" {M}▶ RED{NC}  {D}{iface}{NC}\033[K")
    out.append(f"  {C}IP:{NC} {ip_l:<18} "
               f"{C}↓ {humanize(rx_s, 'B/s')}{NC}  {C}↑ {humanize(tx_s, 'B/s')}{NC}\033[K")
    out.append(f"  {C}Total:{NC} Recibido {humanize(net_stats.bytes_recv)}  "
               f"Enviado {humanize(net_stats.bytes_sent)}\033[K")
    out.append(sep(cols))

    # ── DISCOS ────────────────────────────────────────────────────────────────
    out.append(f" {M}▶ DISCOS{NC}\033[K")
    try:
        io_all = psutil.disk_io_counters(perdisk=True)
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                dev   = p.device.split("/")[-1]
                io_s  = ""
                if dev in io_all:
                    d    = io_all[dev]
                    io_s = f"  {D}R:{humanize(d.read_bytes)} W:{humanize(d.write_bytes)}{NC}"
                out.append(
                    f"  {C}{p.mountpoint:<12}{NC} {barra(usage.percent)}  "
                    f"{C}{humanize(usage.used)} / {humanize(usage.total)}{NC}{io_s}\033[K"
                )
            except PermissionError:
                pass
    except Exception:
        pass
    out.append(sep(cols))

    # ── PROCESOS ─────────────────────────────────────────────────────────────
    out.append(f" {M}▶ TOP PROCESOS{NC}  {D}(cpu%){NC}\033[K")
    out.append(f"  {C}{'PID':>7}  {'CPU%':>5}  {'MEM%':>5}  {'USER':<10}  {'NOMBRE'}{NC}\033[K")
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        max_procs = max(5, shutil.get_terminal_size().lines - len(out) - 4)
        for p in procs[:max_procs]:
            cpu     = p.get("cpu_percent")    or 0.0
            mem     = p.get("memory_percent") or 0.0
            user    = (p.get("username") or "")[:10]
            name    = (p.get("name")     or "")[:28]
            cpu_col = G if cpu < 50 else (Y if cpu < 80 else R)
            out.append(
                f"  {D}{p['pid']:>7}{NC}  {cpu_col}{cpu:>5.1f}{NC}  "
                f"{C}{mem:>5.1f}{NC}  {W}{user:<10}{NC}  {name}\033[K"
            )
    except Exception:
        pass

    out.append(f"\n  {W}q{NC} salir  {D}· refresco {INTERVALO:.0f}s{NC}\033[K")
    out.append("\033[J")
    sys.stdout.write("\n".join(out))
    sys.stdout.flush()

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    static  = get_static()
    backend = static.get("gpu_backend", "none")
    labels  = {
        "nvidia":      "NVIDIA  (nvidia-smi)",
        "amd_rocm":    "AMD     (rocm-smi)",
        "amd_sysfs":   "AMD     (sysfs)",
        "intel_sysfs": "Intel   (sysfs)",
        "none":        "No detectada",
    }
    print(f"GPU detectada: {labels.get(backend, backend)}")
    time.sleep(0.6)

    sys.stdout.write("\033[?1049h\033[?25l\033[2J")
    sys.stdout.flush()
    psutil.cpu_percent(percpu=True)   # calibrar primera muestra

    import select as _sel, tty, termios
    fd      = sys.stdin.fileno()
    old_cfg = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            cols = shutil.get_terminal_size().columns
            render(static, cols)
            r, _, _ = _sel.select([sys.stdin], [], [], INTERVALO)
            if r and sys.stdin.read(1).lower() == "q":
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_cfg)
        salir()

if __name__ == "__main__":
    main()
