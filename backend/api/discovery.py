"""
VERA Office - QR-Code Discovery
Generiert QR-Code mit der VERA-URL für iPad-Discovery.
"""
import io
import socket
from fastapi import APIRouter, Response
from loguru import logger

from backend.config import config

router = APIRouter()

_MDNS_HOSTNAME = "vera-office.local"


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
async def get_qr_code(port: int = None):
    """
    Generiert QR-Code PNG mit der VERA-URL.

    Der QR-Code enthaelt: https://vera-office.local:<port>
    iPad scannt QR -> oeffnet Browser -> fertig.

    Query-Parameter:
    - port: Port (default: konfigurierter Port aus vera.yaml)
    """
    if port is None:
        port = config.PORT
    lan_ip = get_lan_ip()
    # mDNS-Hostname bevorzugen (funktioniert auf iPad/iPhone nativ)
    vera_url = f"https://{_MDNS_HOSTNAME}:{port}"
    
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
                "X-VERA-MDNS": _MDNS_HOSTNAME,
                "Cache-Control": "no-cache"
            }
        )
    except ImportError:
        logger.warning("qrcode-Paket nicht installiert, generiere Text-Fallback")
        return {
            "url": vera_url,
            "ip": lan_ip,
            "mdns": _MDNS_HOSTNAME,
            "port": port,
            "message": "QR-Code-Paket nicht installiert. Bitte oeffnen Sie diese URL auf Ihrem iPad.",
            "install_hint": "pip install qrcode[pil]"
        }


@router.get("/discovery")
async def get_discovery_info():
    """
    Gibt Discovery-Informationen zurueck (IP, URL, Hostname, mDNS).
    Wird vom Frontend genutzt um QR-Code und Zugriffsinfos anzuzeigen.
    """
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()
    port = config.PORT

    return {
        "ip": lan_ip,
        "hostname": hostname,
        "mdns_hostname": _MDNS_HOSTNAME,
        "url": f"https://{_MDNS_HOSTNAME}:{port}",
        "url_ip": f"https://{lan_ip}:{port}",
        "url_http": f"http://{lan_ip}:{port}",
        "port": port,
        "tip": (
            f"iPad/iPhone: Einfach 'https://{_MDNS_HOSTNAME}:{port}' in Safari eingeben. "
            "Empfehlung: Feste IP per DHCP-Reservation im Router einrichten."
        ),
    }
