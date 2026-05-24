"""
Scanner Discovery Service using eSCL/AirScan protocol
Supports automatic scanner discovery via mDNS/zeroconf
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import httpx
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import time
import base64
from lxml import etree

logger = logging.getLogger(__name__)

@dataclass
class Scanner:
    """Represents a discovered scanner"""
    id: str
    name: str
    ip: str
    port: int
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None

class ScannerListener(ServiceListener):
    """mDNS service listener for scanner discovery"""
    
    def __init__(self):
        self.scanners: List[Scanner] = []
        
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered"""
        try:
            info = zc.get_service_info(type_, name)
            if info:
                # Extract scanner information
                ip = None
                if info.addresses:
                    # Convert bytes to IP string
                    ip = '.'.join(str(b) for b in info.addresses[0])
                
                port = info.port
                
                # Get scanner name from properties
                scanner_name = name.split('.')[0]
                if info.properties:
                    scanner_name = info.properties.get(b'ty', scanner_name)
                    if isinstance(scanner_name, bytes):
                        scanner_name = scanner_name.decode('utf-8')
                
                scanner = Scanner(
                    id=f"{ip}:{port}",
                    name=scanner_name,
                    ip=ip,
                    port=port
                )
                
                self.scanners.append(scanner)
                logger.info(f"Discovered scanner: {scanner.name} at {scanner.ip}:{scanner.port}")
        except Exception as e:
            logger.error(f"Error adding scanner service: {e}")
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed"""
        pass
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated"""
        pass

class ScannerDiscovery:
    """Scanner discovery and scanning service"""
    
    ESCL_SERVICES = ['_uscan._tcp.local.', '_uscans._tcp.local.']
    DISCOVERY_TIMEOUT = 5  # seconds
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def discover_scanners(self) -> List[Scanner]:
        """Discover available scanners on the network using mDNS"""
        logger.info("Starting scanner discovery...")
        
        zeroconf = Zeroconf()
        listener = ScannerListener()
        
        try:
            # Browse for both secure and non-secure eSCL services
            browsers = [
                ServiceBrowser(zeroconf, service, listener)
                for service in self.ESCL_SERVICES
            ]
            
            # Wait for discovery
            time.sleep(self.DISCOVERY_TIMEOUT)
            
            # Fetch capabilities for each scanner
            for scanner in listener.scanners:
                try:
                    capabilities = await self._get_scanner_capabilities(scanner)
                    scanner.capabilities = capabilities
                except Exception as e:
                    logger.warning(f"Failed to get capabilities for {scanner.name}: {e}")
            
            logger.info(f"Discovered {len(listener.scanners)} scanner(s)")
            return listener.scanners
            
        except Exception as e:
            logger.error(f"Scanner discovery error: {e}")
            return []
        finally:
            zeroconf.close()
    
    async def _get_scanner_capabilities(self, scanner: Scanner) -> Dict[str, Any]:
        """Get scanner capabilities via eSCL protocol"""
        try:
            url = f"http://{scanner.ip}:{scanner.port}/eSCL/ScannerCapabilities"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            # Parse XML response
            root = etree.fromstring(response.content)
            
            # Extract capabilities
            capabilities = {
                'color_modes': [],
                'resolutions': [],
                'document_formats': []
            }
            
            # Parse color modes
            for mode in root.findall('.//{*}ColorMode'):
                if mode.text:
                    capabilities['color_modes'].append(mode.text)
            
            # Parse resolutions
            for res in root.findall('.//{*}XResolution'):
                if res.text:
                    capabilities['resolutions'].append(int(res.text))
            
            # Parse document formats
            for fmt in root.findall('.//{*}DocumentFormat'):
                if fmt.text:
                    capabilities['document_formats'].append(fmt.text)
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Failed to get scanner capabilities: {e}")
            return {}
    
    async def scan_document(
        self,
        scanner: Scanner,
        resolution: int = 300,
        color_mode: str = 'RGB24',
        format: str = 'image/jpeg'
    ) -> bytes:
        """Scan a document using eSCL protocol"""
        try:
            # Step 1: Create scan job
            job_url = await self._create_scan_job(scanner, resolution, color_mode, format)
            
            if not job_url:
                raise Exception("Failed to create scan job")
            
            # Step 2: Wait a bit for scanner to be ready
            await self._wait_for_scanner()
            
            # Step 3: Get scanned document
            image_data = await self._get_scanned_document(scanner, job_url)
            
            return image_data
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            raise
    
    async def _create_scan_job(
        self,
        scanner: Scanner,
        resolution: int,
        color_mode: str,
        format: str
    ) -> Optional[str]:
        """Create a new scan job"""
        try:
            url = f"http://{scanner.ip}:{scanner.port}/eSCL/ScanJobs"
            
            # Build eSCL scan settings XML
            scan_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03" xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
    <pwg:Version>2.0</pwg:Version>
    <scan:Intent>Document</scan:Intent>
    <pwg:ScanRegions>
        <pwg:ScanRegion>
            <pwg:ContentRegionUnits>escl:ThreeHundredthsOfInches</pwg:ContentRegionUnits>
            <pwg:XOffset>0</pwg:XOffset>
            <pwg:YOffset>0</pwg:YOffset>
            <pwg:Width>2550</pwg:Width>
            <pwg:Height>3300</pwg:Height>
        </pwg:ScanRegion>
    </pwg:ScanRegions>
    <pwg:InputSource>Platen</pwg:InputSource>
    <scan:ColorMode>{color_mode}</scan:ColorMode>
    <scan:XResolution>{resolution}</scan:XResolution>
    <scan:YResolution>{resolution}</scan:YResolution>
    <pwg:DocumentFormat>{format}</pwg:DocumentFormat>
</scan:ScanSettings>"""
            
            headers = {
                'Content-Type': 'text/xml',
            }
            
            response = await self.http_client.post(
                url,
                content=scan_settings,
                headers=headers
            )
            
            response.raise_for_status()
            
            # Extract job URL from Location header
            job_location = response.headers.get('Location')
            if job_location:
                logger.info(f"Created scan job: {job_location}")
                return job_location
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create scan job: {e}")
            return None
    
    async def _wait_for_scanner(self, delay: float = 2.0):
        """Wait for scanner to be ready"""
        import asyncio
        await asyncio.sleep(delay)
    
    async def _get_scanned_document(self, scanner: Scanner, job_url: str) -> bytes:
        """Retrieve scanned document from job"""
        try:
            # Build NextDocument URL
            if job_url.startswith('http'):
                document_url = f"{job_url}/NextDocument"
            else:
                document_url = f"http://{scanner.ip}:{scanner.port}{job_url}/NextDocument"
            
            logger.info(f"Fetching scanned document from: {document_url}")
            
            response = await self.http_client.get(document_url)
            response.raise_for_status()
            
            logger.info(f"Successfully retrieved scanned document ({len(response.content)} bytes)")
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to get scanned document: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

# Singleton instance
_scanner_service: Optional[ScannerDiscovery] = None

def get_scanner_service() -> ScannerDiscovery:
    """Get or create scanner service instance"""
    global _scanner_service
    if _scanner_service is None:
        _scanner_service = ScannerDiscovery()
    return _scanner_service
