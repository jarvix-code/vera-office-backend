"""
VERA Office - Platform-aware Watchdog / Health-Check.

Linux:   systemd watchdog (WATCHDOG=1 / READY=1 via sdnotify)
Windows: Standalone health-check loop (HTTP self-ping, log heartbeat)

Graceful no-op when neither mechanism is available.
"""
import asyncio
import logging
import os
import platform
from typing import Optional

logger = logging.getLogger("vera.watchdog")

#  Platform detection 
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

#  systemd notifier (Linux only) 
_sd_notify = None


def _get_notifier():
    global _sd_notify
    if IS_WINDOWS:
        return False
    if _sd_notify is not None:
        return _sd_notify
    try:
        import sdnotify
        _sd_notify = sdnotify.SystemdNotifier()
        return _sd_notify
    except ImportError:
        logger.debug("sdnotify nicht installiert - systemd Integration deaktiviert")
        _sd_notify = False
        return False


def notify_ready():
    """Signal an systemd: Service ist bereit (Linux) / log ready (Windows)."""
    if IS_WINDOWS:
        logger.info("VERA Watchdog: READY (Windows)")
        return
    n = _get_notifier()
    if n:
        n.notify("READY=1")
        logger.info("systemd: READY=1 gesendet")


def notify_stopping():
    """Signal an systemd: Service wird beendet."""
    if IS_WINDOWS:
        logger.info("VERA Watchdog: STOPPING (Windows)")
        return
    n = _get_notifier()
    if n:
        n.notify("STOPPING=1")


def notify_watchdog():
    """Watchdog ping an systemd (Linux only)."""
    n = _get_notifier()
    if n:
        n.notify("WATCHDOG=1")


def _get_port(port: Optional[int]) -> int:
    if port is not None:
        return port
    try:
        from backend.config import config
        return config.PORT
    except Exception:
        return 8000


#  Windows health-check 
async def _windows_health_check(port: Optional[int] = None) -> bool:
    """Quick HTTP self-ping to verify the VERA backend is responsive."""
    port = _get_port(port)
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.get(f"http://127.0.0.1:{port}/api/system/health") as r:
                return r.status == 200
    except Exception:
        # Fallback: just check the port is open
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port), timeout=3
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False


async def _windows_watchdog_loop(interval: float = 30.0, port: Optional[int] = None):
    """
    Windows health-check loop: pings VERA every *interval* seconds,
    logs warnings on failure.  No auto-restart (that's the service
    manager's job — NSSM / Windows Service Recovery).
    """
    port = _get_port(port)
    logger.info(f"Windows Watchdog aktiv, Interval: {interval:.0f}s, Port: {port}")
    consecutive_failures = 0

    while True:
        await asyncio.sleep(interval)
        ok = await _windows_health_check(port)
        if ok:
            consecutive_failures = 0
            logger.debug("Windows Watchdog: health OK")
        else:
            consecutive_failures += 1
            logger.warning(
                f"Windows Watchdog: health FAIL ({consecutive_failures} in Folge)"
            )
            if consecutive_failures >= 3:
                logger.error(
                    "Windows Watchdog: 3 aufeinanderfolgende Failures — "
                    "Service-Manager sollte Neustart auslösen."
                )


#  Unified entry point 
async def watchdog_loop(interval: float = 25.0, port: Optional[int] = None):
    """
    Platform-aware watchdog loop.
    Linux:   systemd WATCHDOG=1 pings
    Windows: HTTP self-check health loop
    """
    if IS_WINDOWS:
        await _windows_watchdog_loop(interval=30.0, port=port)
        return

    # Linux / systemd path
    n = _get_notifier()
    if not n:
        return

    watchdog_usec = os.environ.get("WATCHDOG_USEC")
    if watchdog_usec:
        interval = int(watchdog_usec) / 1_000_000 / 2
        logger.info(f"systemd Watchdog aktiv, Interval: {interval:.0f}s")
    else:
        logger.debug("WATCHDOG_USEC nicht gesetzt - Watchdog-Loop inaktiv")
        return

    while True:
        notify_watchdog()
        await asyncio.sleep(interval)
