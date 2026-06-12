import psutil
import time
import os
import platform

SERVICE_VERSION = "0.2.0"

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read()) / 1000.0
    except:
        return 0.0

def get_fs_usage():
    usage = psutil.disk_usage('/')
    return {
        "total": usage.total / (1024**3),
        "free": usage.free / (1024**3),
        "percent": usage.percent
    }

def get_os_info():
    return f"{platform.system()} {platform.release()} ({platform.version()})"

def get_system_health():
    return {
        "version": SERVICE_VERSION,
        "os": get_os_info(),
        "cpu_temp": get_cpu_temp(),
        "memory_percent": psutil.virtual_memory().percent,
        "cpu_percent": psutil.cpu_percent(),
        "load_avg": psutil.getloadavg(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "fs": get_fs_usage()
    }
