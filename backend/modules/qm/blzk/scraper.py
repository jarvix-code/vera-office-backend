"""
BLZK Portal Scraper for VERA
Portiert aus D:\QM\backend\app\services\lzk_scraper.py

Login, Session-Management, PDF-Download vom BLZK QM-Portal.
"""
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime
import re
from loguru import logger

# HTTP Client
HTTPX_AVAILABLE = False
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx nicht installiert - pip install httpx")

# HTML Parsing
BS4_AVAILABLE = False
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    logger.warning("beautifulsoup4 nicht installiert - pip install beautifulsoup4")


# BLZK Portal Configuration
BLZK_CONFIG = {
    "name": "Bayerische Landeszahnärztekammer",
    "short_name": "BLZK",
    "base_url": "https://qm.blzk.de",
    "login_url": "https://qm.blzk.de/names.nsf?Login",
    "platform": "lotus_domino",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "timeout": 30,
    "areas": {
        "arbeitssicherheit": "/blzk/web.nsf/arbeitssicherheit",
        "qm": "/blzk/web.nsf/qualitaetsmanagement",
        "hygiene": "/blzk/web.nsf/hygiene",
        "roentgen": "/blzk/web.nsf/roentgen",
        "datenschutz": "/blzk/web.nsf/datenschutz",
    },
    "bundle_agent_url": "/blzk/web.nsf/BundleAgent",
}

DOWNLOAD_DIR = Path("data/blzk_downloads")


class BLZKScraper:
    """BLZK QM-Portal Scraper."""

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.logged_in = False
        self.session_cookies = {}
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        await self.init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def init_client(self):
        """Initialize HTTP client."""
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx nicht verfügbar - pip install httpx")

        self.client = httpx.AsyncClient(
            timeout=float(BLZK_CONFIG["timeout"]),
            follow_redirects=True,
            headers={
                "User-Agent": BLZK_CONFIG["user_agent"],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            }
        )

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.logged_in = False

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login to BLZK QM portal.
        
        Returns:
            Dict with success status and message
        """
        if not self.client:
            await self.init_client()

        try:
            base_url = BLZK_CONFIG["base_url"]
            logger.info("Lade BLZK Login-Seite...")
            login_page = await self.client.get(base_url)

            if login_page.status_code != 200:
                return {"success": False, "error": f"Login-Seite nicht erreichbar: {login_page.status_code}"}

            # Extract form fields (Lotus Domino)
            mod_date = None
            redirect_to = "/blzk/web.nsf"

            if BS4_AVAILABLE:
                soup = BeautifulSoup(login_page.text, 'html.parser')
                md_input = soup.find('input', {'name': '%%ModDate'})
                if md_input:
                    mod_date = md_input.get('value')
                rd_input = soup.find('input', {'name': 'RedirectTo'})
                if rd_input:
                    redirect_to = rd_input.get('value', redirect_to)

            login_data = {
                "Username": username,
                "Password": password,
                "RedirectTo": redirect_to,
            }
            if mod_date:
                login_data["%%ModDate"] = mod_date

            logger.info("Führe BLZK Login durch...")
            response = await self.client.post(
                BLZK_CONFIG["login_url"],
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Check login success
            text = response.text.lower()
            url_str = str(response.url).lower()

            has_logout = "abmelden" in text or "logout" in text
            has_session = any("domauth" in c.lower() for c in self.client.cookies.keys())
            is_portal = "web.nsf" in url_str or "blzk" in url_str
            has_login_form = 'name="username"' in text and 'name="password"' in text

            # Password change required?
            needs_pw_change = any(p in text for p in [
                "passwort ändern", "passwort aendern", "neues passwort", "change password"
            ])

            if needs_pw_change:
                self.logged_in = True
                self.session_cookies = dict(self.client.cookies)
                return {
                    "success": True,
                    "message": "Login erfolgreich - Passwortänderung erforderlich",
                    "needs_password_change": True
                }

            # Failure indicators
            is_failure = any(p in text for p in [
                "ungültig", "ungueltig", "invalid", "login fehlgeschlagen",
                "falsches kennwort", "wrong password"
            ])

            is_success = (is_portal or has_logout or has_session) and not is_failure

            if is_success:
                self.logged_in = True
                self.session_cookies = dict(self.client.cookies)
                logger.success("BLZK Login erfolgreich!")
                return {"success": True, "message": "Login erfolgreich"}
            else:
                error_msg = self._extract_error(response.text)
                logger.warning(f"BLZK Login fehlgeschlagen: {error_msg}")
                return {"success": False, "error": error_msg or "Login fehlgeschlagen - Zugangsdaten prüfen"}

        except httpx.ConnectError:
            return {"success": False, "error": f"Verbindung zu {BLZK_CONFIG['base_url']} fehlgeschlagen"}
        except Exception as e:
            logger.error(f"Login-Fehler: {e}")
            return {"success": False, "error": str(e)}

    async def get_document_ids(self, area: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all document IDs from portal areas.
        
        Args:
            area: Optional specific area key to scan
            
        Returns:
            Dict with document IDs per area
        """
        if not self.logged_in:
            return {"success": False, "error": "Nicht eingeloggt"}
        if not BS4_AVAILABLE:
            return {"success": False, "error": "BeautifulSoup nicht installiert"}

        areas = BLZK_CONFIG["areas"]
        if area and area in areas:
            areas = {area: areas[area]}

        result = {}
        base = BLZK_CONFIG["base_url"]

        for area_name, path in areas.items():
            try:
                response = await self.client.get(f"{base}{path}")
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    doc_ids = [
                        cb.get('value', '')
                        for cb in soup.find_all('input', {'type': 'checkbox', 'name': 'documents[]'})
                        if cb.get('value', '') and len(cb.get('value', '')) > 20
                    ]
                    result[area_name] = {"count": len(doc_ids), "doc_ids": doc_ids}
                    logger.info(f"Bereich {area_name}: {len(doc_ids)} Dokumente")
            except Exception as e:
                result[area_name] = {"count": 0, "doc_ids": [], "error": str(e)}

        return {
            "success": True,
            "areas": result,
            "total_documents": sum(r.get("count", 0) for r in result.values())
        }

    async def download_bundle(self, doc_ids: List[str], filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Download PDF bundle from portal.
        
        Args:
            doc_ids: List of document IDs
            filename: Optional filename (without .pdf)
            
        Returns:
            Dict with download status and file path
        """
        if not self.logged_in:
            return {"success": False, "error": "Nicht eingeloggt"}
        if not doc_ids:
            return {"success": False, "error": "Keine Dokument-IDs"}

        base = BLZK_CONFIG["base_url"]
        bundle_url = f"{base}{BLZK_CONFIG['bundle_agent_url']}"
        
        # Split into chunks of 20
        chunks = [doc_ids[i:i+20] for i in range(0, len(doc_ids), 20)]
        downloaded = []
        errors = []

        for idx, chunk in enumerate(chunks):
            try:
                docids_str = "|".join(chunk) + "|"
                response = await self.client.post(
                    bundle_url,
                    data={"docids": docids_str},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=120.0
                )

                if response.status_code == 200:
                    content = response.content
                    is_pdf = content[:4] == b'%PDF'

                    if is_pdf and len(content) > 1000:
                        if filename:
                            save_name = f"{filename}.pdf" if len(chunks) == 1 else f"{filename}_teil{idx+1}.pdf"
                        else:
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            save_name = f"blzk_bundle_{ts}_teil{idx+1}.pdf"

                        save_path = DOWNLOAD_DIR / save_name
                        save_path.write_bytes(content)

                        downloaded.append({
                            "chunk_index": idx,
                            "doc_count": len(chunk),
                            "saved_as": str(save_path),
                            "size_bytes": len(content),
                            "size_mb": round(len(content) / (1024*1024), 2)
                        })
                        logger.success(f"Bundle {idx+1} heruntergeladen: {save_name}")
                    else:
                        # Try extracting PDF URL from HTML
                        pdf_url = self._extract_pdf_url(content.decode('utf-8', errors='ignore'))
                        if pdf_url:
                            if not pdf_url.startswith('http'):
                                pdf_url = f"{base}{pdf_url}" if pdf_url.startswith('/') else f"{base}/{pdf_url}"
                            pdf_resp = await self.client.get(pdf_url, timeout=120.0)
                            if pdf_resp.status_code == 200 and pdf_resp.content[:4] == b'%PDF':
                                save_name = f"{filename or 'blzk_bundle'}_{idx+1}.pdf"
                                save_path = DOWNLOAD_DIR / save_name
                                save_path.write_bytes(pdf_resp.content)
                                downloaded.append({
                                    "chunk_index": idx,
                                    "doc_count": len(chunk),
                                    "saved_as": str(save_path),
                                    "size_bytes": len(pdf_resp.content)
                                })
                                continue
                        errors.append({"chunk_index": idx, "error": "Kein PDF erhalten"})
                else:
                    errors.append({"chunk_index": idx, "error": f"HTTP {response.status_code}"})
            except Exception as e:
                errors.append({"chunk_index": idx, "error": str(e)})

        return {
            "success": len(downloaded) > 0,
            "downloaded": downloaded,
            "total_documents": len(doc_ids),
            "errors": errors or None,
            "download_dir": str(DOWNLOAD_DIR)
        }

    def _extract_pdf_url(self, html: str) -> Optional[str]:
        """Extract PDF URL from HTML response."""
        for pattern in [
            r'window\.location\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']',
            r'href\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']',
            r'href\s*=\s*["\']([^"\']*\$file[^"\']*)["\']',
        ]:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_error(self, html: str) -> Optional[str]:
        """Extract error message from HTML."""
        if not BS4_AVAILABLE:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        for sel in ['.error', '.alert-danger', '.alert-error', '#error']:
            el = soup.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return None


# Singleton
blzk_scraper = BLZKScraper()
