def render(static: dict, cols: int, first_render: bool = False):
    out_lines = []
    
    out_lines.append("\033[H")
    
    # ─── SISTEMA ────────────────────────────────────────────────────────────
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
    out_lines.append(f"  {C}OS:{NC} {static['os']:<33} {C}MB:{NC} {static['mb']}\033[K")
    out_lines.append(f"  {C}Uptime:{NC} {uptime:<20} {C}Load:{NC} {load_s}\033[K")
    out_lines.append(sep(cols))
    
    # ─── CPU ────────────────────────────────────────────────────────────────
    out_lines.append(f" {M}▶ CPU{NC}  {D}{static['cpu_model'][:55]}{NC}\033[K")
    
    cpu_pcts = psutil.cpu_percent(percpu=True)
    temps_core, temp_global = get_cpu_temps()
    g_pct = psutil.cpu_percent()
    g_temp_s = f"  {color_temp(temp_global)}{temp_global:.0f}°C{NC}" if temp_global else ""
    
    # CORREGIDO: CPU Total con barra
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
    
    # ─── GPU ────────────────────────────────────────────────────────────────
    if IS_WINDOWS:
        gpu_name, gpu_usage, gpu_temp = get_gpu_info_windows()
    else:
        gpu_name, gpu_usage, gpu_temp = get_gpu_info_linux()
    
    out_lines.append(f" {M}▶ GPU{NC}  {D}{gpu_name[:45]}{NC}\033[K")
    out_lines.append(f"  {C}{'Uso':<8}{NC} {barra(gpu_usage)}\033[K")
    if gpu_temp:
        out_lines.append(f"  {C}Temp{NC}     {color_temp(gpu_temp)}{gpu_temp:.0f}°C{NC}\033[K")
    out_lines.append(sep(cols))
    
    # ─── TEMPERATURAS DISCOS ────────────────────────────────────────────────
    disk_temps = get_disk_temps()
    if disk_temps:
        out_lines.append(f" {M}▶ DISCOS (TEMP){NC}\033[K")
        for disk, temp in list(disk_temps.items())[:5]:
            out_lines.append(f"  {C}{disk[:20]:<20}{NC} {color_temp(temp)}{temp:5.1f}°C{NC}\033[K")
        out_lines.append(sep(cols))
    
    # ─── RECURSOS ───────────────────────────────────────────────────────────
    out_lines.append(f" {M}▶ RECURSOS{NC}\033[K")
    mem = psutil.virtual_memory()
    out_lines.append(f"  {C}{'RAM':<8}{NC} {barra(mem.percent)}  {C}{humanize(mem.used)} / {humanize(mem.total)}{NC}\033[K")
    
    swap_info = get_swap_or_virtual()
    out_lines.append(f"  {C}{swap_info['name']:<8}{NC} {barra(swap_info['percent'])}  {C}{humanize(swap_info['used'])} / {humanize(swap_info['total'])}{NC}\033[K")
    out_lines.append(sep(cols))
    
    # ─── RED ────────────────────────────────────────────────────────────────
    net_stats, rx_s, tx_s = get_net_speed()
    out_lines.append(f" {M}▶ RED{NC}  {D}{iface}{NC}\033[K")
    out_lines.append(f"  {C}IP:{NC} {ip_l:<18} {C}↓ {humanize(rx_s, 'B/s')}{NC}  {C}↑ {humanize(tx_s, 'B/s')}{NC}\033[K")
    out_lines.append(f"  {C}Total:{NC} ↓ {humanize(net_stats.bytes_recv)}  ↑ {humanize(net_stats.bytes_sent)}\033[K")
    out_lines.append(sep(cols))
    
    # ─── DISCOS (USO) - CORREGIDO ───────────────────────────────────────────
    out_lines.append(f" {M}▶ DISCOS (USO){NC}\033[K")
    try:
        for p in psutil.disk_partitions():
            try:
                if IS_WINDOWS:
                    # Mostrar discos C:, D:, E: etc.
                    if len(p.mountpoint) == 2 and p.mountpoint[1] == ':':
                        usage = psutil.disk_usage(p.mountpoint)
                        out_lines.append(f"  {C}{p.mountpoint[:4]:<6}{NC} {barra(usage.percent)}  {C}{humanize(usage.used)} / {humanize(usage.total)}{NC}\033[K")
                else:
                    if p.mountpoint in ['/', '/home']:
                        usage = psutil.disk_usage(p.mountpoint)
                        out_lines.append(f"  {C}{p.mountpoint[:12]:<12}{NC} {barra(usage.percent)}  {C}{humanize(usage.used)} / {humanize(usage.total)}{NC}\033[K")
            except:
                pass
    except:
        pass
    out_lines.append(sep(cols))
    
    # ─── TOP PROCESOS ───────────────────────────────────────────────────────
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
    max_procs = max(4, min(available_lines, 8))
    
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
    
    # ─── FOOTER ────────────────────────────────────────────────────────────
    out_lines.append(f"\n  {W}q{NC} salir  {D}· refresco {INTERVALO:.0f}s{NC}\033[K")
    out_lines.append("\033[J")
    
    sys.stdout.write("\n".join(out_lines))
    sys.stdout.flush()
