"""
Scanner API endpoints
Provides scanner discovery and scanning functionality
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import base64
from backend.core.scanner_discovery import get_scanner_service, Scanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scanner", tags=["scanner"])

class ScannerInfo(BaseModel):
    """Scanner information response model"""
    id: str
    name: str
    ip: str
    port: int
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None

class ScanRequest(BaseModel):
    """Scan request model"""
    scanner_id: str
    resolution: int = 300
    color_mode: str = "RGB24"
    format: str = "image/jpeg"

class ScanResponse(BaseModel):
    """Scan response model"""
    success: bool
    image_data: Optional[str] = None  # Base64 encoded
    format: str
    size_bytes: int
    message: Optional[str] = None

class DiscoverResponse(BaseModel):
    """Scanner discovery response model"""
    scanners: List[ScannerInfo]
    count: int

@router.get("/discover", response_model=DiscoverResponse)
async def discover_scanners():
    """
    Discover available scanners on the network
    
    Returns list of discovered scanners with their capabilities
    """
    try:
        scanner_service = get_scanner_service()
        scanners = await scanner_service.discover_scanners()
        
        scanner_infos = [
            ScannerInfo(
                id=scanner.id,
                name=scanner.name,
                ip=scanner.ip,
                port=scanner.port,
                model=scanner.model,
                manufacturer=scanner.manufacturer,
                capabilities=scanner.capabilities
            )
            for scanner in scanners
        ]
        
        logger.info(f"Discovered {len(scanner_infos)} scanner(s)")
        
        return DiscoverResponse(
            scanners=scanner_infos,
            count=len(scanner_infos)
        )
        
    except Exception as e:
        logger.error(f"Scanner discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scanner discovery failed: {str(e)}")

@router.post("/scan", response_model=ScanResponse)
async def scan_document(request: ScanRequest):
    """
    Scan a document from a specific scanner
    
    - **scanner_id**: Scanner identifier (ip:port)
    - **resolution**: Scan resolution in DPI (default: 300)
    - **color_mode**: Color mode (RGB24, Grayscale8, BlackAndWhite1)
    - **format**: Output format (image/jpeg, image/png, application/pdf)
    """
    try:
        # Parse scanner ID
        parts = request.scanner_id.split(':')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid scanner_id format. Expected 'ip:port'")
        
        ip, port_str = parts
        try:
            port = int(port_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid port in scanner_id")
        
        # Create Scanner object
        scanner = Scanner(
            id=request.scanner_id,
            name="Scanner",
            ip=ip,
            port=port
        )
        
        # Perform scan
        scanner_service = get_scanner_service()
        
        logger.info(f"Starting scan from {scanner.name} ({scanner.ip}:{scanner.port})")
        
        image_bytes = await scanner_service.scan_document(
            scanner=scanner,
            resolution=request.resolution,
            color_mode=request.color_mode,
            format=request.format
        )
        
        # Encode to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        logger.info(f"Scan completed successfully ({len(image_bytes)} bytes)")
        
        return ScanResponse(
            success=True,
            image_data=image_base64,
            format=request.format,
            size_bytes=len(image_bytes),
            message="Scan completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for scanner service
    """
    return {
        "status": "ok",
        "service": "scanner",
        "message": "Scanner service is running"
    }
