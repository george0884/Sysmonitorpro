import platform
import subprocess

IS_WINDOWS = platform.system() == "Windows"

print("=" * 50)
print("DIAGNÓSTICO DE GPU")
print("=" * 50)

if IS_WINDOWS:
    print("\n1. Verificando GPUtil...")
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            for gpu in gpus:
                print(f"   ✅ GPU: {gpu.name}")
                print(f"      Uso: {gpu.load*100:.1f}%")
                print(f"      Temp: {gpu.temperature}°C")
        else:
            print("   ❌ No se detectaron GPUs con GPUtil")
    except ImportError:
        print("   ❌ GPUtil no instalado (pip install gputil)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n2. Verificando WMI...")
    try:
        import wmi
        w = wmi.WMI()
        for gpu in w.Win32_VideoController():
            print(f"   ✅ GPU: {gpu.Name}")
    except ImportError:
        print("   ❌ WMI no instalado (pip install wmi pywin32)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n3. Verificando OpenHardwareMonitor...")
    try:
        result = subprocess.run(['tasklist', '/fi', 'imagename eq OpenHardwareMonitor.exe'], 
                               capture_output=True, text=True)
        if 'OpenHardwareMonitor.exe' in result.stdout:
            print("   ✅ OpenHardwareMonitor está corriendo")
        else:
            print("   ❌ OpenHardwareMonitor NO está corriendo")
            print("      Descargar de: https://openhardwaremonitor.org/")
    except:
        pass
    
    print("\n4. Verificando registro...")
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
            r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000")
        gpu_name = winreg.QueryValueEx(key, "DriverDesc")[0]
        print(f"   ✅ GPU del registro: {gpu_name}")
        winreg.CloseKey(key)
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print("\n1. Verificando nvidia-smi...")
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ GPU: {result.stdout.strip()}")
        else:
            print("   ❌ nvidia-smi no disponible")
    except:
        print("   ❌ nvidia-smi no encontrado")

print("\n" + "=" * 50)
