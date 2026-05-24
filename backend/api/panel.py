"""
VERA Office - Status Panel
Für 5-Zoll Touchdisplay am AOOSTAR Mini-PC (800x480, Fullscreen-Browser)
Routes: GET /panel, GET /api/panel/status, GET /api/panel/qr, POST /api/panel/reboot
"""
import io
import os
import platform
import socket
import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from loguru import logger
from sqlalchemy.orm import Session

from backend.api.discovery import get_lan_ip
from backend.config import config
from backend.db.database import SessionLocal
from backend.models.document import Document

router = APIRouter()

_startup_time = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# /api/panel/status
# ---------------------------------------------------------------------------

@router.get("/api/panel/status")
async def panel_status():
    """Systemgesundheit für das Status-Panel."""
    # CPU / RAM / Disk
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(config.DATA_DIR))

    ram_used_gb = round(mem.used / (1024 ** 3), 1)
    ram_total_gb = round(mem.total / (1024 ** 3), 1)

    # Uptime
    uptime_seconds = int((datetime.now(timezone.utc) - _startup_time).total_seconds())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m"

    # Letzte OCR-Verarbeitung (neuestes Dokument in DB)
    last_ocr_str = "—"
    try:
        db: Session = SessionLocal()
        last_doc = (
            db.query(Document.created_at)
            .filter(Document.deleted == False)
            .order_by(Document.created_at.desc())
            .first()
        )
        db.close()
        if last_doc and last_doc[0]:
            ts = last_doc[0]
            if hasattr(ts, "strftime"):
                last_ocr_str = ts.strftime("%H:%M %d.%m.")
    except Exception:
        pass

    # LLM-Status (lazy — prüfe ob Manager verfügbar ist)
    llm_status = "unbekannt"
    llm_response_ms = None
    try:
        from backend.core.ai.llm_manager import LLMManager
        mgr = LLMManager()
        if mgr.is_available():
            llm_status = "OK"
        else:
            llm_status = "nicht geladen"
    except Exception:
        llm_status = "nicht verfügbar"

    return JSONResponse({
        "cpu_percent": cpu,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "ram_percent": round(mem.percent, 1),
        "disk_percent": round(disk.percent, 1),
        "disk_used_gb": round(disk.used / (1024 ** 3), 1),
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "llm_status": llm_status,
        "llm_response_ms": llm_response_ms,
        "last_ocr": last_ocr_str,
        "uptime": uptime_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# /api/panel/qr
# ---------------------------------------------------------------------------

def _get_vera_url() -> str:
    """Gibt die primäre VERA-URL zurück (HTTPS wenn Caddy-Cert vorhanden, sonst HTTP)."""
    lan_ip = get_lan_ip()
    cert_path = config.BASE_DIR / "certs" / "vera.crt"
    if cert_path.exists():
        https_port = getattr(config, "HTTPS_PORT", 8443)
        return f"https://{lan_ip}:{https_port}"
    return f"http://{lan_ip}:{config.PORT}"


@router.get("/api/panel/qr")
async def panel_qr():
    """QR-Code PNG mit der VERA LAN-URL (HTTPS wenn Caddy aktiv)."""
    vera_url = _get_vera_url()

    try:
        import qrcode

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=3,
        )
        qr.add_data(vera_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#ffffff", back_color="#111111")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={
                "X-VERA-URL": vera_url,
                "Cache-Control": "no-cache",
            },
        )
    except ImportError:
        # Fallback: leeres 1x1 PNG damit <img> nicht bricht
        logger.warning("qrcode-Paket nicht installiert (pip install qrcode[pil])")
        return Response(status_code=503, content="qrcode not installed")


# ---------------------------------------------------------------------------
# /api/panel/reboot
# ---------------------------------------------------------------------------

@router.post("/api/panel/reboot")
async def panel_reboot(request: Request):
    """
    Startet das System neu.
    Nur erlaubt wenn der Request von localhost (127.0.0.1 / ::1) kommt.
    """
    client_ip = request.client.host if request.client else ""
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        logger.warning(f"Reboot verweigert von: {client_ip}")
        return JSONResponse(
            status_code=403,
            content={"error": "Reboot nur vom lokalen Gerät erlaubt."},
        )

    logger.warning(f"System-Neustart angefordert von {client_ip}")
    import asyncio

    async def _do_reboot():
        await asyncio.sleep(1)
        if platform.system() == "Windows":
            os.system("shutdown /r /t 5")
        else:
            os.system("systemctl reboot || shutdown -r now")

    asyncio.create_task(_do_reboot())
    return JSONResponse({"status": "rebooting", "message": "System wird in 5 Sekunden neu gestartet."})


# ---------------------------------------------------------------------------
# /panel  — standalone HTML-Seite (kein Vue, kein Build)
# ---------------------------------------------------------------------------

_PANEL_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=800, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>VERA Status Panel</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:      #0a0a0a;
    --bg2:     #111111;
    --bg3:     #1a1a1a;
    --border:  #2a2a2a;
    --text:    #e8e8e8;
    --dim:     #888888;
    --green:   #22c55e;
    --yellow:  #eab308;
    --red:     #ef4444;
    --blue:    #3b82f6;
    --accent:  #6366f1;
  }

  html, body {
    width: 800px; height: 480px;
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    overflow: hidden;
    -webkit-tap-highlight-color: transparent;
  }

  /* ── Layout ─────────────────────────────────────────────── */
  #app {
    display: grid;
    grid-template-columns: 220px 1fr;
    grid-template-rows: 1fr 88px;
    width: 800px; height: 480px;
    gap: 0;
  }

  /* ── QR Panel (links) ───────────────────────────────────── */
  #qr-panel {
    grid-row: 1 / 2;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    padding: 12px 10px 8px;
    gap: 8px;
  }
  #qr-panel img {
    width: 160px; height: 160px;
    border-radius: 8px;
    background: #111;
  }
  #qr-url {
    font-size: 11px;
    color: var(--dim);
    text-align: center;
    word-break: break-all;
    line-height: 1.4;
  }
  #qr-label {
    font-size: 10px;
    color: var(--dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  #https-hint {
    font-size: 10px;
    color: #22c55e;
    text-align: center;
    line-height: 1.4;
    padding: 3px 6px;
    background: #052e16;
    border-radius: 4px;
  }

  /* ── Stats Panel (rechts oben) ──────────────────────────── */
  #stats-panel {
    grid-row: 1 / 2;
    padding: 14px 16px;
    display: flex; flex-direction: column; gap: 10px;
    overflow: hidden;
  }

  .stat-row {
    display: flex; align-items: center; gap: 10px;
  }
  .stat-label {
    font-size: 12px;
    color: var(--dim);
    width: 100px;
    flex-shrink: 0;
  }
  .stat-value {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.02em;
  }
  .stat-bar-wrap {
    flex: 1;
    background: var(--bg3);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
  }
  .stat-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.4s ease;
  }
  .bar-green  { background: var(--green); }
  .bar-yellow { background: var(--yellow); }
  .bar-red    { background: var(--red); }

  .chip {
    display: inline-flex; align-items: center;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 12px; font-weight: 600;
    gap: 4px;
  }
  .chip-green  { background: #052e16; color: var(--green); }
  .chip-yellow { background: #422006; color: var(--yellow); }
  .chip-red    { background: #450a0a; color: var(--red); }
  .chip-gray   { background: #1a1a1a; color: var(--dim); }

  .dot { width: 7px; height: 7px; border-radius: 50%; }
  .dot-green  { background: var(--green); }
  .dot-yellow { background: var(--yellow); }
  .dot-red    { background: var(--red); }
  .dot-gray   { background: var(--dim); }

  /* Uptime + letzter Scan (kleinere Zeile) */
  .stat-mini {
    display: flex; gap: 24px; align-items: center;
    padding-top: 4px;
    border-top: 1px solid var(--border);
    margin-top: 4px;
  }
  .mini-label { font-size: 11px; color: var(--dim); }
  .mini-value { font-size: 13px; color: var(--text); font-weight: 500; }

  /* Refresh indicator */
  #refresh-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--accent);
    opacity: 0;
    margin-left: auto;
    transition: opacity 0.3s;
  }
  #refresh-dot.active { opacity: 1; }

  /* ── Reset Button (volle Breite unten) ──────────────────── */
  #reset-area {
    grid-column: 1 / 3;
    grid-row: 2 / 3;
    border-top: 1px solid var(--border);
    display: flex; align-items: stretch;
  }

  #btn-reboot {
    flex: 1;
    background: #1a0505;
    border: none;
    color: var(--red);
    font-size: 18px; font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: background 0.2s;
    user-select: none;
    display: flex; align-items: center; justify-content: center; gap: 12px;
  }
  #btn-reboot:hover  { background: #250808; }
  #btn-reboot.active { background: #2d0a0a; }

  /* SVG ring progress */
  #ring-wrap {
    position: relative; width: 44px; height: 44px;
    display: none;
  }
  #ring-wrap.visible { display: block; }
  #ring-bg { stroke: #3d1010; }
  #ring-fg {
    stroke: var(--red);
    stroke-dasharray: 113;
    stroke-dashoffset: 113;
    transition: stroke-dashoffset 0.05s linear;
    transform-origin: 50% 50%;
    transform: rotate(-90deg);
  }
  #ring-pct {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%,-50%);
    font-size: 13px; font-weight: 700; color: var(--red);
  }

  /* Confirm Dialog */
  #confirm-overlay {
    display: none;
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.85);
    align-items: center; justify-content: center;
    z-index: 100;
  }
  #confirm-overlay.show { display: flex; }
  #confirm-box {
    background: var(--bg2);
    border: 1px solid var(--red);
    border-radius: 12px;
    padding: 28px 32px;
    text-align: center;
    max-width: 340px;
  }
  #confirm-box h2 { font-size: 20px; color: var(--red); margin-bottom: 10px; }
  #confirm-box p  { font-size: 14px; color: var(--dim); margin-bottom: 24px; line-height: 1.5; }
  .confirm-btns   { display: flex; gap: 12px; justify-content: center; }
  .btn-yes {
    background: var(--red); color: #fff;
    border: none; border-radius: 8px;
    padding: 12px 28px; font-size: 16px; font-weight: 700;
    cursor: pointer;
  }
  .btn-no {
    background: var(--bg3); color: var(--text);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 12px 28px; font-size: 16px;
    cursor: pointer;
  }

  /* Reboot countdown overlay */
  #reboot-overlay {
    display: none;
    position: fixed; inset: 0;
    background: #000;
    align-items: center; justify-content: center;
    flex-direction: column; gap: 16px;
    z-index: 200;
  }
  #reboot-overlay.show { display: flex; }
  #reboot-overlay h1 { font-size: 28px; color: var(--red); }
  #reboot-overlay p  { font-size: 14px; color: var(--dim); }
</style>
</head>
<body>
<div id="app">

  <!-- QR Code (links) -->
  <div id="qr-panel">
    <div id="qr-label">iPad / Handy</div>
    <img id="qr-img" src="/api/panel/qr" alt="QR Code" />
    <div id="qr-url">Laden…</div>
    <div id="https-hint">HTTPS — Cert beim 1. Besuch akzeptieren</div>
  </div>

  <!-- System Stats (rechts oben) -->
  <div id="stats-panel">

    <!-- CPU -->
    <div class="stat-row">
      <span class="stat-label">CPU</span>
      <span class="stat-value" id="cpu-val">—</span>
      <div class="stat-bar-wrap">
        <div class="stat-bar bar-green" id="cpu-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- RAM -->
    <div class="stat-row">
      <span class="stat-label">RAM</span>
      <span class="stat-value" id="ram-val">—</span>
      <div class="stat-bar-wrap">
        <div class="stat-bar bar-green" id="ram-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- Disk -->
    <div class="stat-row">
      <span class="stat-label">Disk</span>
      <span class="stat-value" id="disk-val">—</span>
      <div class="stat-bar-wrap">
        <div class="stat-bar bar-green" id="disk-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- LLM -->
    <div class="stat-row">
      <span class="stat-label">LLM-Modell</span>
      <span id="llm-chip" class="chip chip-gray">
        <span class="dot dot-gray" id="llm-dot"></span>
        <span id="llm-txt">—</span>
      </span>
    </div>

    <!-- Uptime + Letzte OCR -->
    <div class="stat-mini">
      <div>
        <div class="mini-label">Uptime</div>
        <div class="mini-value" id="uptime-val">—</div>
      </div>
      <div>
        <div class="mini-label">Letzte OCR</div>
        <div class="mini-value" id="ocr-val">—</div>
      </div>
      <div id="refresh-dot"></div>
    </div>

  </div>

  <!-- Reset Button (unten, volle Breite) -->
  <div id="reset-area">
    <button id="btn-reboot" ontouchstart="holdStart(event)" ontouchend="holdEnd(event)"
            onmousedown="holdStart(event)" onmouseup="holdEnd(event)" onmouseleave="holdEnd(event)">
      <div id="ring-wrap">
        <svg width="44" height="44" viewBox="0 0 44 44">
          <circle id="ring-bg" cx="22" cy="22" r="18" fill="none" stroke-width="4"/>
          <circle id="ring-fg" cx="22" cy="22" r="18" fill="none" stroke-width="4" stroke-linecap="round"/>
        </svg>
        <div id="ring-pct">3</div>
      </div>
      <span id="btn-label">⟳ System Neustart</span>
    </button>
  </div>

</div>

<!-- Bestätigungs-Dialog -->
<div id="confirm-overlay">
  <div id="confirm-box">
    <h2>Wirklich neustarten?</h2>
    <p>VERA wird heruntergefahren.<br>Alle laufenden Prozesse werden beendet.</p>
    <div class="confirm-btns">
      <button class="btn-no" onclick="cancelReboot()">Abbrechen</button>
      <button class="btn-yes" onclick="confirmReboot()">Jetzt neustarten</button>
    </div>
  </div>
</div>

<!-- Neustart-Meldung -->
<div id="reboot-overlay">
  <h1>Neustart wird durchgeführt…</h1>
  <p>Das System startet in wenigen Sekunden neu.</p>
</div>

<script>
// ── Status Refresh ────────────────────────────────────────────────────────
async function refreshStatus() {
  const dot = document.getElementById('refresh-dot');
  dot.classList.add('active');
  setTimeout(() => dot.classList.remove('active'), 400);

  try {
    const r = await fetch('/api/panel/status');
    if (!r.ok) return;
    const d = await r.json();

    // CPU
    setBar('cpu-val', 'cpu-bar', d.cpu_percent, '%');

    // RAM
    document.getElementById('ram-val').textContent =
      d.ram_used_gb + ' / ' + d.ram_total_gb + ' GB';
    setBarRaw('ram-bar', d.ram_percent);

    // Disk
    setBar('disk-val', 'disk-bar', d.disk_percent, '%');

    // LLM
    const chip = document.getElementById('llm-chip');
    const dot2 = document.getElementById('llm-dot');
    const txt  = document.getElementById('llm-txt');
    txt.textContent = d.llm_status;
    if (d.llm_status === 'OK') {
      chip.className = 'chip chip-green';
      dot2.className = 'dot dot-green';
    } else if (d.llm_status === 'nicht geladen') {
      chip.className = 'chip chip-yellow';
      dot2.className = 'dot dot-yellow';
    } else {
      chip.className = 'chip chip-gray';
      dot2.className = 'dot dot-gray';
    }

    document.getElementById('uptime-val').textContent = d.uptime;
    document.getElementById('ocr-val').textContent   = d.last_ocr;

  } catch(e) { /* silent */ }
}

function setBar(valId, barId, pct, suffix) {
  document.getElementById(valId).textContent = pct + (suffix || '');
  setBarRaw(barId, pct);
}

function setBarRaw(barId, pct) {
  const bar = document.getElementById(barId);
  bar.style.width = Math.min(pct, 100) + '%';
  bar.className = 'stat-bar ' + (
    pct >= 90 ? 'bar-red' : pct >= 70 ? 'bar-yellow' : 'bar-green'
  );
}

// ── QR URL Text ───────────────────────────────────────────────────────────
async function loadQrUrl() {
  try {
    const r = await fetch('/api/panel/qr', { method: 'HEAD' });
    const url = r.headers.get('X-VERA-URL') || window.location.origin;
    document.getElementById('qr-url').textContent = url;
  } catch(e) {
    document.getElementById('qr-url').textContent = window.location.origin;
  }
}

// ── Hold-to-Reboot ────────────────────────────────────────────────────────
let holdTimer   = null;
let holdStart_t = null;
const HOLD_MS   = 3000;
const CIRCUMFERENCE = 2 * Math.PI * 18; // ≈ 113

function holdStart(e) {
  e.preventDefault();
  if (holdTimer) return;
  const btn   = document.getElementById('btn-reboot');
  const ring  = document.getElementById('ring-wrap');
  const fg    = document.getElementById('ring-fg');
  const pct   = document.getElementById('ring-pct');
  const label = document.getElementById('btn-label');

  btn.classList.add('active');
  ring.classList.add('visible');
  label.style.display = 'none';
  holdStart_t = Date.now();

  function tick() {
    const elapsed = Date.now() - holdStart_t;
    const progress = Math.min(elapsed / HOLD_MS, 1);
    const offset = CIRCUMFERENCE * (1 - progress);
    fg.style.strokeDashoffset = offset;
    const secs = Math.ceil((HOLD_MS - elapsed) / 1000);
    pct.textContent = secs > 0 ? secs : '✓';

    if (progress < 1) {
      holdTimer = requestAnimationFrame(tick);
    } else {
      // 3 Sekunden gehalten — Dialog zeigen
      resetHoldUI();
      document.getElementById('confirm-overlay').classList.add('show');
    }
  }
  holdTimer = requestAnimationFrame(tick);
}

function holdEnd(e) {
  if (holdTimer) {
    cancelAnimationFrame(holdTimer);
    holdTimer = null;
  }
  resetHoldUI();
}

function resetHoldUI() {
  if (holdTimer) { cancelAnimationFrame(holdTimer); holdTimer = null; }
  const btn   = document.getElementById('btn-reboot');
  const ring  = document.getElementById('ring-wrap');
  const fg    = document.getElementById('ring-fg');
  const label = document.getElementById('btn-label');
  btn.classList.remove('active');
  ring.classList.remove('visible');
  fg.style.strokeDashoffset = CIRCUMFERENCE;
  label.style.display = '';
}

function cancelReboot() {
  document.getElementById('confirm-overlay').classList.remove('show');
}

async function confirmReboot() {
  document.getElementById('confirm-overlay').classList.remove('show');
  document.getElementById('reboot-overlay').classList.add('show');
  try {
    await fetch('/api/panel/reboot', { method: 'POST' });
  } catch(e) { /* System geht runter — Fehler erwartet */ }
}

// ── Init ──────────────────────────────────────────────────────────────────
loadQrUrl();
refreshStatus();
setInterval(refreshStatus, 5000);
</script>
</body>
</html>"""


@router.get("/panel", response_class=HTMLResponse, include_in_schema=False)
async def panel_page():
    """Status-Panel für 5-Zoll Touchdisplay."""
    return HTMLResponse(content=_PANEL_HTML)
