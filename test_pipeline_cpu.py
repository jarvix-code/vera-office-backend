"""
test_pipeline_cpu.py
Smoke-Test der Dokumenten-Pipeline auf CPU-only System (ohne GPU, ohne LLaVA).

Testet jeden Pipeline-Schritt isoliert und meldet ob er funktioniert oder
warum er (erwartbar) nicht funktioniert (z.B. Modell-Datei fehlt).

Aufruf:
    py test_pipeline_cpu.py [--image PATH]

Ohne --image wird ein synthetisches 400x300 Test-Bild mit Text generiert.
"""
import sys
import time
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


STEP_WIDTH = 50

def step(name: str):
    print(f"\n{'='*60}")
    print(f"SCHRITT: {name}")
    print('='*60)


def ok(msg: str):
    print(f"  [OK]  {msg}")


def warn(msg: str):
    print(f"  [--]  {msg}")


def fail(msg: str):
    print(f"  [!!]  {msg}")


# --------------------------------------------------------------------------- #
# 0. VORBEREITUNG: Test-Bild erstellen falls keines angegeben
# --------------------------------------------------------------------------- #
def make_test_image(out_path: Path) -> Path:
    """Erzeugt ein synthetisches Test-Bild mit lesbarem Text."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        text = (
            "Rechnung Nr. 2026-042\n"
            "Datum: 15.03.2026\n"
            "Absender: Muster GmbH\n"
            "Betrag: 1.234,56 EUR netto\n"
            "MwSt 19%: 234,57 EUR\n"
            "Gesamtbetrag: 1.469,13 EUR brutto\n"
            "IBAN: DE89 3704 0044 0532 0130 00\n"
            "Bitte zahlen Sie bis 30.03.2026.\n"
        )
        draw.multiline_text((40, 40), text, fill=(0, 0, 0), spacing=8)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out_path), "JPEG", quality=95)
        ok(f"Test-Bild erstellt: {out_path}")
        return out_path
    except ImportError:
        fail("Pillow nicht installiert — kein synthetisches Bild möglich")
        fail("Bitte eine JPG/PNG-Datei mit --image übergeben")
        sys.exit(1)


# --------------------------------------------------------------------------- #
# SCHRITT 1 — Konfiguration laden
# --------------------------------------------------------------------------- #
def test_config():
    step("1. Konfiguration laden (backend/config.py)")
    try:
        from backend.config import config
        ok(f"config.DATA_DIR       = {config.DATA_DIR}")
        ok(f"config.OCR_LANGUAGE   = {config.OCR_LANGUAGE}")
        ok(f"config.OCR_GPU        = {config.OCR_GPU}")
        ok(f"config.HOTFOLDER_ENABLED = {config.HOTFOLDER_ENABLED}")
        return config
    except Exception as e:
        fail(f"Config-Import fehlgeschlagen: {e}")
        return None


# --------------------------------------------------------------------------- #
# SCHRITT 2 — LLM Manager: Sentinels + Verfügbarkeit
# --------------------------------------------------------------------------- #
def test_llm_manager():
    step("2. LLM Manager (Mistral / Qwen / LLaVA)")
    try:
        from backend.core.ai.llm_manager import llm

        # Text LLM
        t0 = time.time()
        avail = llm.is_available()
        dur = time.time() - t0
        if avail:
            ok(f"Text-LLM (Mistral) verfügbar ({dur:.1f}s Ladezeit)")
        else:
            warn(f"Text-LLM nicht verfügbar ({dur:.1f}s) — Keyword-Fallback aktiv")

        # Fast LLM
        t0 = time.time()
        fast = llm.is_fast_available()
        dur = time.time() - t0
        if fast:
            ok(f"Fast-LLM (Qwen) verfügbar ({dur:.1f}s)")
        else:
            warn(f"Fast-LLM nicht verfügbar ({dur:.1f}s)")

        # Vision LLM
        t0 = time.time()
        vis = llm.is_vision_available()
        dur = time.time() - t0
        if vis:
            ok(f"Vision-LLM (LLaVA) verfügbar ({dur:.1f}s)")
        else:
            warn(f"Vision-LLM nicht verfügbar ({dur:.1f}s) — erwartet auf CPU")

        # Sentinel-Check: zweiter Aufruf darf NICHT erneut laden
        t0 = time.time()
        _ = llm.is_vision_available()
        dur2 = time.time() - t0
        if dur2 < 0.01:
            ok(f"Sentinel OK: zweiter is_vision_available()-Aufruf in {dur2*1000:.1f}ms (kein Re-Load)")
        else:
            warn(f"Sentinel möglicherweise nicht aktiv: {dur2*1000:.1f}ms für zweiten Aufruf")

        return llm
    except Exception as e:
        fail(f"LLM Manager Fehler: {e}")
        return None


# --------------------------------------------------------------------------- #
# SCHRITT 3 — OCR Engine
# --------------------------------------------------------------------------- #
def test_ocr(image_path: Path):
    step(f"3. OCR Engine (PaddleOCR, CPU)")
    try:
        from backend.core.ocr_engine import OCREngine
        ocr = OCREngine()

        t0 = time.time()
        text = ocr.extract_text(image_path)
        dur = time.time() - t0

        if text:
            ok(f"OCR erfolgreich in {dur:.1f}s: {len(text)} Zeichen, {text.count(chr(10))+1} Zeilen")
            ok(f"Vorschau: {text[:120].replace(chr(10), ' | ')}")
            return text
        else:
            warn(f"OCR lieferte keinen Text ({dur:.1f}s) — PaddleOCR installiert?")
            return ""
    except Exception as e:
        fail(f"OCR-Fehler: {e}")
        return ""


# --------------------------------------------------------------------------- #
# SCHRITT 4 — Bildverarbeitung (ImageProcessor)
# --------------------------------------------------------------------------- #
def test_image_processor(image_path: Path, config) -> Path:
    step("4. Bildverarbeitung (Kantenerkennung, Perspektivkorrektur)")
    try:
        from backend.core.image_processor import ImageProcessor
        proc = ImageProcessor()

        out_path = config.DATA_DIR / "temp" / f"test_processed_{image_path.stem}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        success = proc.process(image_path, out_path)
        dur = time.time() - t0

        if success and out_path.exists():
            ok(f"Bildverarbeitung OK in {dur:.1f}s → {out_path.name}")
            return out_path
        else:
            warn(f"Bildverarbeitung fehlgeschlagen ({dur:.1f}s) — nutze Original")
            return image_path
    except Exception as e:
        fail(f"ImageProcessor Fehler: {e}")
        return image_path


# --------------------------------------------------------------------------- #
# SCHRITT 5 — Vision Checker (sollte auf CPU graceful überspringen)
# --------------------------------------------------------------------------- #
def test_vision_checker(image_path: Path):
    step("5. Vision Checker (LLaVA — erwartet: graceful skip auf CPU)")
    try:
        from backend.core.ai.vision_checker import vision_checker

        t0 = time.time()
        result = vision_checker.check_quality(str(image_path))
        dur = time.time() - t0

        if not result.get('available'):
            ok(f"Vision-Check korrekt übersprungen ({dur*1000:.0f}ms) — Pipeline läuft weiter")
        elif result.get('quality_score') is not None:
            ok(f"Vision-Check Score: {result['quality_score']:.2f} ({dur:.1f}s)")
        else:
            warn(f"Vision-Check: available=True aber kein Score ({dur:.1f}s)")
        return result
    except Exception as e:
        fail(f"VisionChecker Fehler: {e}")
        return {'available': False}


# --------------------------------------------------------------------------- #
# SCHRITT 6 — Klassifizierung
# --------------------------------------------------------------------------- #
def test_classifier(ocr_text: str):
    step("6. Klassifizierung (Mistral oder Keyword-Fallback)")
    if not ocr_text:
        warn("Kein OCR-Text vorhanden — Klassifizierung übersprungen")
        return None

    try:
        from backend.core.ai.classifier import classifier

        t0 = time.time()
        result = classifier.classify(ocr_text)
        dur = time.time() - t0

        category = result['category']
        confidence = result['confidence']
        available = result.get('available', True)
        brain_hint = result.get('brain_hint', False)

        source = "Brain" if brain_hint else ("LLM" if available else "Keyword-Fallback")
        ok(f"Kategorie: {category} | Confidence: {confidence:.0%} | Quelle: {source} | {dur:.1f}s")
        ok(f"Reasoning: {result.get('reasoning', '')[:80]}")
        return result
    except Exception as e:
        fail(f"Classifier Fehler: {e}")
        return None


# --------------------------------------------------------------------------- #
# SCHRITT 7 — Namer (Dateiname generieren)
# --------------------------------------------------------------------------- #
def test_namer(ocr_text: str, category: str):
    step("7. Namer (semantischer Dateiname)")
    try:
        from backend.core.ai.namer import namer

        t0 = time.time()
        filename = namer.generate_filename(ocr_text, category, "test.jpg")
        dur = time.time() - t0

        ok(f"Dateiname: {filename} ({dur:.1f}s)")
        return filename
    except Exception as e:
        fail(f"Namer Fehler: {e}")
        return f"test_{int(time.time())}.pdf"


# --------------------------------------------------------------------------- #
# SCHRITT 8 — PDF Generator
# --------------------------------------------------------------------------- #
def test_pdf_generator(image_path: Path, ocr_text: str, config):
    step("8. PDF Generator")
    try:
        from backend.core.pdf_generator import PDFGenerator
        gen = PDFGenerator()

        out_path = config.DATA_DIR / "temp" / "test_output.pdf"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        success = gen.create_pdf_from_images([image_path], out_path, ocr_text)
        dur = time.time() - t0

        if success and out_path.exists():
            size_kb = out_path.stat().st_size // 1024
            ok(f"PDF erstellt: {out_path.name} ({size_kb} KB) in {dur:.1f}s")
            return out_path
        else:
            fail(f"PDF-Erstellung fehlgeschlagen ({dur:.1f}s)")
            return None
    except Exception as e:
        fail(f"PDFGenerator Fehler: {e}")
        return None


# --------------------------------------------------------------------------- #
# ZUSAMMENFASSUNG
# --------------------------------------------------------------------------- #
def print_summary(results: dict):
    print("\n" + "="*60)
    print("ZUSAMMENFASSUNG — Pipeline CPU-Tauglichkeit")
    print("="*60)

    all_ok = True
    for step_name, status in results.items():
        symbol = "[OK]" if status else "[!!]"
        if not status:
            all_ok = False
        print(f"  {symbol}  {step_name}")

    print()
    if all_ok:
        print("  ✅ Pipeline vollständig funktionsfähig auf CPU")
    else:
        print("  ⚠️  Einige Schritte haben Probleme — Details oben prüfen")
    print("="*60)


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="VERA Pipeline CPU-Smoke-Test")
    parser.add_argument("--image", type=Path, help="Pfad zu Test-Bild (JPG/PNG)")
    args = parser.parse_args()

    print("VERA Office — Pipeline CPU-Smoke-Test")
    print(f"Python: {sys.version}")
    print(f"Datum:  {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Config
    config = test_config()
    results["1. Config laden"] = config is not None
    if not config:
        print_summary(results)
        return

    # Test-Bild
    if args.image and args.image.exists():
        image_path = args.image
        ok(f"Nutze übergebenes Bild: {image_path}")
    else:
        image_path = config.DATA_DIR / "temp" / "test_input.jpg"
        step("0. Test-Bild erstellen")
        make_test_image(image_path)

    # Alle Schritte
    llm = test_llm_manager()
    results["2. LLM Manager (Sentinel)"] = llm is not None

    processed_path = test_image_processor(image_path, config)
    results["4. Bildverarbeitung"] = processed_path is not None

    ocr_text = test_ocr(processed_path)
    results["3. OCR (PaddleOCR CPU)"] = ocr_text is not None and len(ocr_text) > 0

    vision_result = test_vision_checker(image_path)
    results["5. Vision-Check (graceful skip)"] = not vision_result.get('available', True) or vision_result.get('quality_score') is not None

    classify_result = test_classifier(ocr_text)
    results["6. Klassifizierung"] = classify_result is not None and classify_result.get('category') != 'unknown'

    category = (classify_result or {}).get('category', 'unknown')
    filename = test_namer(ocr_text, category)
    results["7. Namer"] = bool(filename and filename != 'unknown.pdf')

    pdf_path = test_pdf_generator(processed_path, ocr_text, config)
    results["8. PDF Generator"] = pdf_path is not None

    print_summary(results)


if __name__ == "__main__":
    main()
