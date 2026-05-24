# VERA Office — Dual-Platform Setup (Windows + Linux)

## Platform Detection

VERA auto-detects the OS at runtime. No config needed.

```python
import platform
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
```

Used in: `core/systemd_watchdog.py`, `api/usb_import.py`

---

## Feature Matrix

| Feature | Windows | Linux |
|---------|---------|-------|
| **Backend (FastAPI)** | ✅ | ✅ |
| **USB Import** | ✅ Win32 `GetDriveTypeW` + Fallback | ✅ `/media/`, `/mnt/usb` |
| **Watchdog** | ✅ HTTP health-check loop | ✅ systemd WATCHDOG=1 |
| **Service Install** | ✅ NSSM (`tools/install_windows_service.ps1`) | ✅ systemd unit file |
| **Scanner (eSCL/Network)** | ✅ zeroconf/mDNS | ✅ zeroconf/mDNS |
| **Scanner (Local/USB)** | ⏳ WIA/TWAIN (planned) | ⏳ SANE (planned) |
| **Hotfolder Watcher** | ✅ watchdog (cross-platform) | ✅ watchdog (cross-platform) |

---

## Windows Setup

### 1. Install & Run (Development)
```powershell
cd C:\Jarvix\vera-office
python -m venv venv
.\venv\Scripts\pip install -r backend\requirements.txt
.\venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 2. Install as Windows Service (Production)
```powershell
# Install NSSM: https://nssm.cc/download  or  choco install nssm
# Then (run as Administrator):
.\tools\install_windows_service.ps1
```

Service management:
```powershell
nssm status VERA-Office
nssm stop VERA-Office
nssm start VERA-Office
nssm restart VERA-Office
# Uninstall:
.\tools\install_windows_service.ps1 -Uninstall
```

### 3. USB Import on Windows
- Plug in USB stick → appears as `D:\`, `E:\`, etc.
- VERA detects removable drives via Win32 `GetDriveTypeW`
- Fallback: checks `D:`–`H:` if ctypes unavailable

---

## Linux Setup

### 1. Install as systemd Service
```bash
sudo cp docker/vera-office.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vera-office
```

### 2. USB Import on Linux
- Auto-mount USB to `/media/usb0/` or `/media/<label>/`
- Fallback: `/mnt/usb/`

---

## Architecture Notes

- **Watchdog** (`core/systemd_watchdog.py`): Single entry point `watchdog_loop()` dispatches to platform-specific implementation
- **USB Detection** (`api/usb_import.py`): `_find_usb_mount()` → `_find_usb_windows()` / `_find_usb_linux()`
- **Scanner Discovery**: Uses eSCL/AirScan over network (cross-platform, no SANE/WIA needed)
- **Hotfolder**: Python `watchdog` library works on both platforms natively
