"""
VERA Office - QR-Code Discovery
Generiert QR-Code mit der VERA-URL für iPad-Discovery.
"""
import io
import socket
from fastapi import APIRouter, Response
from loguru import logger

router = APIRouter()


def get_lan_ip() -> str:
    """Ermittelt die LAN-IP-Adresse des Rechners."""
    try:
        # UDP-Socket Trick: Verbindet sich nicht wirklich, ermittelt aber die richtige LAN-IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback: alle Interfaces durchgehen
        try:
            hostname = socket.gethostname()
            ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for ip_info in ips:
                ip = ip_info[4][0]
                if not ip.startswith("127."):
                    return ip
        except Exception:
            pass
    return "127.0.0.1"


@router.get("/qr")
async def get_qr_code(port: int = 8443):
    """
    Generiert QR-Code PNG mit der VERA-URL.
    
    Der QR-Code enthaelt: https://<LAN-IP>:<port>
    iPad scannt QR -> oeffnet Browser -> fertig.
    
    Query-Parameter:
    - port: Port (default 8443 fuer HTTPS, 8000 fuer HTTP)
    """
    lan_ip = get_lan_ip()
    vera_url = f"https://{lan_ip}:{port}"
    
    try:
        import qrcode
        from qrcode.image.pil import PilImage
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(vera_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        logger.info(f"QR-Code generiert fuer: {vera_url}")
        
        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={
                "X-VERA-URL": vera_url,
                "X-VERA-IP": lan_ip,
                "Cache-Control": "no-cache"
            }
        )
    except ImportError:
        logger.warning("qrcode-Paket nicht installiert, generiere Text-Fallback")
        return {
            "url": vera_url,
            "ip": lan_ip,
            "port": port,
            "message": "QR-Code-Paket nicht installiert. Bitte oeffnen Sie diese URL auf Ihrem iPad.",
            "install_hint": "pip install qrcode[pil]"
        }


@router.get("/discovery")
async def get_discovery_info(port: int = 8443):
    """
    Gibt Discovery-Informationen zurueck (IP, URL, Hostname).
    Wird vom Frontend genutzt um QR-Code anzuzeigen.
    """
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()
    
    return {
        "ip": lan_ip,
        "hostname": hostname,
        "url": f"https://{lan_ip}:{port}",
        "url_http": f"http://{lan_ip}:8000",
        "port_https": port,
        "port_http": 8000,
        "tip": "Empfehlung: Richten Sie eine feste IP-Adresse (DHCP-Reservation) fuer diesen PC ein, damit sich die URL nicht aendert."
    }
