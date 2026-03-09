"""
mDNS / Bonjour Service - Advertises VERA Office on local network.
Allows discovery via vera-office.local from iPad/iPhone.
Registers both HTTP service AND hostname A-record.
"""
import logging
import socket
from typing import Optional
from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


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


class MDNSService:
    """mDNS/Bonjour service for local network discovery."""
    
    def __init__(self):
        """Initialize mDNS service."""
        self.zeroconf: Optional[Zeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        self.host_info: Optional[ServiceInfo] = None
        self.registered = False
    
    def register(self, port: int = 8000, service_name: str = "vera-office"):
        """Register mDNS service + hostname."""
        if self.registered:
            logger.warning("mDNS service already registered")
            return
        
        try:
            local_ip = _get_local_ip()
            ip_bytes = socket.inet_aton(local_ip)
            
            # 1) Register HTTP service
            service_type = "_http._tcp.local."
            full_name = f"{service_name}.{service_type}"
            
            self.service_info = ServiceInfo(
                service_type,
                full_name,
                addresses=[ip_bytes],
                port=port,
                properties={
                    'version': '1.0.0',
                    'app': 'VERA Office',
                    'path': '/'
                },
                server=f"{service_name}.local."
            )
            
            # 2) Register a dummy service that forces the hostname
            # This makes vera-office.local resolve to our IP
            self.host_info = ServiceInfo(
                "_vera._tcp.local.",
                f"VERA Office._vera._tcp.local.",
                addresses=[ip_bytes],
                port=port,
                server=f"{service_name}.local."
            )
            
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            self.zeroconf.register_service(self.host_info)
            
            self.registered = True
            
            logger.info(f"mDNS registered: http://{service_name}.local:{port}")
            logger.info(f"LAN IP: {local_ip}")
        
        except Exception as e:
            logger.error(f"Failed to register mDNS service: {e}")
            self.registered = False
    
    def unregister(self):
        """Unregister mDNS service."""
        if not self.registered:
            return
        
        try:
            if self.zeroconf and self.service_info:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                logger.info("mDNS service unregistered")
        
        except Exception as e:
            logger.error(f"Failed to unregister mDNS service: {e}")
        
        finally:
            self.registered = False
            self.zeroconf = None
            self.service_info = None
    
    def is_registered(self) -> bool:
        """Check if service is registered."""
        return self.registered


# Global instance
mdns_service = MDNSService()
