"""
mDNS / Bonjour Service - Advertises VERA Office on local network.
Allows discovery via vera-office.local from iPad/iPhone.

IMPLEMENTATION: AsyncZeroconf with allow_name_change=True + Singleton Pattern
Based on Home Assistant best practices.
"""
import socket
from typing import Optional
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf
from loguru import logger


def find_free_port(preferred: int = 8000, max_attempts: int = 10) -> int:
    """
    Find a free TCP port starting from preferred.
    Returns preferred if available, otherwise tries preferred+1, +2, ...
    Raises RuntimeError if no port found in range.
    """
    for port in range(preferred, preferred + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"Kein freier Port im Bereich {preferred}-{preferred + max_attempts - 1} gefunden"
    )


def _get_local_ip() -> str:
    """Get the LAN IP address (not 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


class VERAMDNSService:
    """
    mDNS/Bonjour service for local network discovery.
    Singleton pattern with AsyncZeroconf for proper async support.
    """
    _instance = None  # Singleton
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize mDNS service (Singleton)."""
        self.zeroconf: Optional[AsyncZeroconf] = None
        self.service_info: Optional[AsyncServiceInfo] = None
        self.registered = False
    
    async def register(self, port: int = 8000, service_name: str = "vera-office"):
        """Register mDNS service with async-native Zeroconf."""
        if self.registered:
            logger.warning("mDNS service already registered")
            return
        
        try:
            self.zeroconf = AsyncZeroconf()
            
            # Service Info
            service_type = "_https._tcp.local."
            full_name = f"{service_name}.{service_type}"
            
            # Properties
            properties = {
                "path": "/",
                "version": "1.0.0",
                "app": "VERA Office"
            }
            
            # Get IP
            hostname = socket.gethostname()
            local_ip = _get_local_ip()
            
            # AsyncServiceInfo with allow_name_change
            self.service_info = AsyncServiceInfo(
                service_type,
                full_name,
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties=properties,
                server=f"{hostname}.local."
            )
            
            # Register (async-native, auto-retry on name conflicts)
            await self.zeroconf.async_register_service(
                self.service_info,
                allow_name_change=True
            )
            
            self.registered = True
            
            logger.info(f"[OK] mDNS registered: https://{service_name}.local:{port}")
            logger.info(f"LAN IP: {local_ip}")
            
        except Exception as e:
            logger.error(f"[ERROR] mDNS registration failed: {type(e).__name__}: {e}")
            self.registered = False
    
    async def unregister(self):
        """Unregister mDNS service with proper cleanup."""
        if not self.registered:
            return

        try:
            if self.service_info and self.zeroconf:
                await self.zeroconf.async_unregister_service(self.service_info)
            if self.zeroconf:
                await self.zeroconf.async_close()
            logger.info("[OK] mDNS unregistered")

        except Exception as e:
            logger.warning(f"[WARNING] mDNS unregister error (non-critical): {e}")

        finally:
            self.registered = False
            self.zeroconf = None
            self.service_info = None
    
    def is_registered(self) -> bool:
        """Check if service is registered."""
        return self.registered


# Global instance (Singleton)
mdns_service = VERAMDNSService.get_instance()
