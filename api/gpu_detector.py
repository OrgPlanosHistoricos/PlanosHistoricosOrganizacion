"""
Detector de hardware GPU (NVIDIA vs AMD vs CPU).
Inspecciona controladores del sistema, dispositivos y estado de Ollama.
"""
import glob
import json
import logging
import os
import subprocess
import urllib.request
from typing import Dict, Any

logger = logging.getLogger("planos.gpu_detector")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")


def _detectar_desde_wsl_drivers() -> Dict[str, str]:
    """Detecta drivers montados en WSL2 (/usr/lib/wsl/drivers o /lib/wsl/drivers)."""
    for wsl_drivers_path in ["/usr/lib/wsl/drivers", "/lib/wsl/drivers"]:
        if os.path.isdir(wsl_drivers_path):
            try:
                entradas = os.listdir(wsl_drivers_path)
                for entrada in entradas:
                    e_lower = entrada.lower()
                    if "nv_" in e_lower or "nvidia" in e_lower:
                        return {"tipo": "NVIDIA", "backend": "cuda", "nombre": "NVIDIA (WSL2/CUDA)"}
                    if "amd" in e_lower or "radeon" in e_lower:
                        return {"tipo": "AMD", "backend": "rocm", "nombre": "AMD Radeon (WSL2/ROCm)"}
            except Exception as exc:
                logger.debug(f"No se pudo leer {wsl_drivers_path}: {exc}")
    return {}


def _detectar_desde_dispositivos() -> Dict[str, str]:
    """Detecta nodos de dispositivos en /dev o /proc."""
    # NVIDIA en Linux / Docker
    if os.path.exists("/proc/driver/nvidia") or glob.glob("/dev/nvidia*"):
        return {"tipo": "NVIDIA", "backend": "cuda", "nombre": "NVIDIA GPU (CUDA)"}

    # AMD en Linux / Docker
    if os.path.exists("/dev/kfd") or os.path.exists("/sys/module/amdgpu"):
        return {"tipo": "AMD", "backend": "rocm", "nombre": "AMD Radeon (ROCm)"}

    # DirectX Graphics de WSL2
    if os.path.exists("/dev/dxg"):
        wsl_info = _detectar_desde_wsl_drivers()
        if wsl_info:
            return wsl_info
        return {"tipo": "NVIDIA", "backend": "cuda", "nombre": "GPU Acelerada (WSL2)"}

    return {}


def _detectar_desde_windows_host() -> Dict[str, str]:
    """Si se ejecuta directamente en Windows (fuera de contenedor)."""
    if os.name == "nt":
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            out = res.stdout.strip()
            for line in out.splitlines():
                l_strip = line.strip()
                if "nvidia" in l_strip.lower():
                    return {"tipo": "NVIDIA", "backend": "cuda", "nombre": l_strip}
                if "amd" in l_strip.lower() or "radeon" in l_strip.lower():
                    return {"tipo": "AMD", "backend": "rocm", "nombre": l_strip}
        except Exception:
            pass
    return {}


def _consultar_ollama_vram() -> bool:
    """Verifica si Ollama tiene soporte/capas en VRAM cargadas."""
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/ps")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                for m in data.get("models", []):
                    if m.get("size_vram", 0) > 0:
                        return True
    except Exception:
        pass
    return False


def detectar_hardware_gpu() -> Dict[str, Any]:
    """
    Detecta la GPU disponible en el sistema (NVIDIA o AMD).
    Retorna un diccionario con estado, tipo y nombre legible.
    """
    # 1. Probar dispositivos del sistema o WSL
    info = _detectar_desde_dispositivos()

    # 2. Si no encontró y está en Windows nativo
    if not info:
        info = _detectar_desde_windows_host()

    # 3. Si no encontró por drivers pero Ollama reporta VRAM activa
    if not info and _consultar_ollama_vram():
        info = {"tipo": "NVIDIA", "backend": "cuda", "nombre": "GPU Acelerada (Ollama)"}

    if info:
        return {
            "gpu_disponible": True,
            "tipo": info["tipo"],
            "backend": info.get("backend", "gpu"),
            "nombre": info.get("nombre", f"GPU {info['tipo']}"),
        }

    return {
        "gpu_disponible": False,
        "tipo": "CPU",
        "backend": "cpu",
        "nombre": "CPU (sin GPU dedicada detectada)",
    }

