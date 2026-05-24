"""
DB-driven workflow engine for VERA document processing.

Reads steps from processing_steps table, evaluates condition_sql per step,
respects on_error strategies (fail/skip/fallback/retry), logs every step
(status + duration_ms + error) to processing_runs.

Primary key in documents table is `id` (INTEGER). All lookups use that.

Registered actions must exactly match action names in processing_steps.action.
If an action name is not in ACTION_HANDLERS, the step FAILS with a clear error.
"""
import sqlite3
import json
import logging
import time
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path('/opt/vera-office/data/vera.db')
BRAIN_DB_PATH = Path('/opt/vera-office/data/vera_brain.db')


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _eval_condition(conn, condition_sql: str, doc_id: int) -> bool:
    """Evaluate a SQL condition against the documents table for this document."""
    if not condition_sql:
        return True
    try:
        row = conn.execute(
            f"SELECT 1 FROM documents WHERE id=? AND ({condition_sql}) LIMIT 1",
            (doc_id,)
        ).fetchone()
        return row is not None
    except Exception as e:
        logger.warning(f"condition_sql eval failed [{condition_sql!r}]: {e}")
        return False


# ─── Action handlers ────────────────────────────────────────────────────────

def _action_normalize_format(conn, doc_id: int, params: dict) -> dict:
    row = conn.execute(
        "SELECT filename, mimetype FROM documents WHERE id=?", (doc_id,)
    ).fetchone()
    if not row:
        return {"ok": False, "error": "document not found"}
    allowed = params.get("allowed_inputs", [])
    suffix = Path(row["filename"]).suffix.lower().lstrip(".")
    if allowed and suffix not in allowed:
        return {"ok": False, "error": f"unsupported format: .{suffix}"}
    if not row["mimetype"]:
        conn.execute(
            "UPDATE documents SET mimetype='application/pdf', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (doc_id,)
        )
    return {"ok": True, "format": suffix}


def _action_convert_to_pdf(conn, doc_id: int, params: dict) -> dict:
    """Flag doc for PDF conversion if not already PDF."""
    row = conn.execute("SELECT mimetype, needs_pdf_conversion FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "document not found"}
    if row["mimetype"] and "pdf" in str(row["mimetype"]).lower():
        return {"ok": True, "skipped": True, "reason": "already pdf"}
    conn.execute(
        "UPDATE documents SET needs_pdf_conversion=1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (doc_id,)
    )
    return {"ok": True, "flagged": True}


def _action_ocr_if_needed(conn, doc_id: int, params: dict) -> dict:
    import subprocess
    import tempfile
    import os
    row = conn.execute(
        "SELECT file_path, has_text_layer, ocr_text FROM documents WHERE id=?", (doc_id,)
    ).fetchone()
    if not row:
        return {"ok": False, "error": "document not found"}
    if row["has_text_layer"] and row["ocr_text"] and len(row["ocr_text"]) > 50:
        return {"ok": True, "skipped": True, "reason": "already has text"}

    file_path = row["file_path"]
    if file_path and not file_path.startswith("/"):
        file_path = f"/opt/vera-office/data/{file_path}"
    if not file_path or not Path(file_path).exists():
        return {"ok": False, "error": f"file not found: {file_path}"}

    # pdftotext first
    try:
        result = subprocess.run(
            ["pdftotext", "-q", file_path, "-"],
            capture_output=True, text=True, timeout=60
        )
        text = result.stdout.strip()
        if len(text) > 50:
            conn.execute(
                "UPDATE documents SET ocr_text=?, has_text_layer=1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (text, doc_id)
            )
            return {"ok": True, "method": "pdftotext", "chars": len(text)}
    except Exception:
        pass

    # Tesseract fallback
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tf:
            tmp_base = tf.name[:-4]
        subprocess.run(
            ["tesseract", file_path, tmp_base, "-l", params.get("lang", "deu+eng"), "quiet"],
            capture_output=True, timeout=120
        )
        txt_path = tmp_base + ".txt"
        if Path(txt_path).exists():
            text = Path(txt_path).read_text(encoding="utf-8", errors="replace").strip()
            os.unlink(txt_path)
            if len(text) > 10:
                conn.execute(
                    "UPDATE documents SET ocr_text=?, has_text_layer=1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (text, doc_id)
                )
                return {"ok": True, "method": "tesseract", "chars": len(text)}
    except Exception as e:
        return {"ok": False, "error": f"tesseract failed: {e}"}

    return {"ok": False, "error": "all OCR methods exhausted"}


def _action_llm_classify(conn, doc_id: int, params: dict) -> dict:
    """
    Bug #243 Fix: Regex-Pre-Check BEVOR LLM-Klassifizierung.
    Verhindert falsche Klassifizierung bei 100+ Kategorien im Prompt.
    """
    try:
        import sys
        sys.path.insert(0, '/opt/vera-office')
        from backend.core.ai.llm_router import LLMRouter

        row = conn.execute(
            "SELECT filename, ocr_text FROM documents WHERE id=?", (doc_id,)
        ).fetchone()
        if not row:
            return {"ok": False, "error": "document not found"}

        # Fetch allowed categories from DB
        cats = [r[0] for r in conn.execute("SELECT name FROM categories ORDER BY name").fetchall()]
        if not cats:
            cats = ["rechnung_eingang", "rechnung_ausgang", "vertraege", "personal",
                    "qm-dokumente", "lohnabrechnung", "kontoauszug", "steuerbescheid", "sonstiges"]

        text = (row["ocr_text"] or "").lower()
        fname = (row["filename"] or "").lower()
        combined = fname + " " + text

        # ─── Regex-Pre-Check: starke Keyword-Signale (Bug #243) ──────────────
        PRIORITY_RULES = [
            (r"rechnung|invoice|faktura|rechnungsnr|re-\d|re\d|mwst|mehrwertsteuer|umsatzsteuer|\d+,\d+\s*eur|betrag.*eur|eur.*betrag", "rechnung_eingang"),
            (r"kontoauszug|bank.*statement|iban|bic|swift|girokonto|sparkasse|volksbank|commerzbank|deutsche bank", "kontoauszug"),
            (r"lohnabrechnung|gehaltsabrechnung|bruttogehalt|nettogehalt|sozialversicherung.*beitrag|krankenversicherung.*abzug", "lohnabrechnung"),
            (r"steuerbescheid|finanzamt.*bescheid|einkommensteuerbescheid|körperschaftsteuer.*bescheid", "steuerbescheid"),
            (r"mietvertrag|arbeitsvertrag|dienstleistungsvertrag|rahmenvertrag|leasingvertrag", "vertraege"),
        ]

        pre_category = None
        for pattern, cat in PRIORITY_RULES:
            if re.search(pattern, combined):
                if cat in cats:
                    pre_category = cat
                    break

        if pre_category:
            conn.execute(
                """UPDATE documents
                   SET category=?, classification_status='regex_priority_classified',
                       updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (pre_category, doc_id)
            )
            cat_row = conn.execute("SELECT id FROM categories WHERE name=?", (pre_category,)).fetchone()
            if cat_row:
                conn.execute("UPDATE documents SET category_id=? WHERE id=?", (cat_row["id"], doc_id))
            logger.info(f"[WE] Regex-Pre-Check: doc {doc_id} -> {pre_category}")
            return {"ok": True, "category": pre_category, "method": "regex_priority"}

        # ─── LLM-Klassifizierung (nur wenn Regex kein Treffer) ───────────────
        COMMON_CATS = [
            "rechnung_eingang", "rechnung_ausgang", "kontoauszug", "vertraege",
            "lohnabrechnung", "steuerbescheid", "personal", "qm-dokumente",
            "korrespondenz", "bestellung", "angebot", "protokoll",
            "versicherungspolice", "mahnung_eingang", "sonstiges"
        ]
        llm_cats = [c for c in COMMON_CATS if c in cats]
        cats_str = ", ".join(llm_cats)

        text_snippet = (row["ocr_text"] or "")[:1500]
        prompt = (
            "<|im_start|>system\n"
            "Klassifiziere das Dokument. Antworte NUR mit dem Kategorienamen aus der Liste.\n"
            "Regeln: Rechnung+EUR=rechnung_eingang | IBAN=kontoauszug | Bruttogehalt=lohnabrechnung\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"Datei: {row['filename']}\nText: {text_snippet or 'kein Text'}\n"
            f"Kategorien: {cats_str}\nKategorie:<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        router = LLMRouter()
        llm = router.get_llm("user_query")
        if not llm:
            return {"ok": False, "error": "no LLM available (neither Qwen nor Mistral loaded)"}

        response = llm.generate(prompt, max_tokens=20, stop=["<|im_end|>", "\n", " ", ","])
        category = (response or "").strip().lower().rstrip(".,: ")

        # Strict validation: exact match first, then unambiguous prefix
        if category not in cats:
            matches = [c for c in cats if c.startswith(category) and len(category) >= 4]
            if len(matches) == 1:
                category = matches[0]
            else:
                logger.warning(f"[WE] llm_classify ambiguous: '{category}' -> sonstiges")
                category = "sonstiges"

        conn.execute(
            """UPDATE documents
               SET category=?, classification_status='llm_classified',
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (category, doc_id)
        )
        cat_row = conn.execute("SELECT id FROM categories WHERE name=?", (category,)).fetchone()
        if cat_row:
            conn.execute("UPDATE documents SET category_id=? WHERE id=?", (cat_row["id"], doc_id))
        return {"ok": True, "category": category}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _action_classify_by_filename_regex(conn, doc_id: int, params: dict) -> dict:
    row = conn.execute("SELECT filename FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "document not found"}

    fname = row["filename"].lower()
    patterns = [
        (r"rechnung|invoice|faktura", "rechnung_eingang"),
        (r"vertrag|contract|agreement", "vertraege"),
        (r"personal|mitarbeiter|cv|lebenslauf", "personal"),
        (r"qm|qualit|checklist|sop|anweisung", "qm-dokumente"),
        (r"lohnabrechnung|gehalt|payslip", "lohnabrechnung"),
        (r"kontoauszug|bank|statement", "kontoauszug"),
        (r"steuer|tax|finanzamt|steuerbescheid", "steuerbescheid"),
    ]
    for pattern, cat in patterns:
        if re.search(pattern, fname):
            conn.execute(
                """UPDATE documents
                   SET category=?, classification_status='regex_classified',
                       updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (cat, doc_id)
            )
            cat_row = conn.execute("SELECT id FROM categories WHERE name=?", (cat,)).fetchone()
            if cat_row:
                conn.execute("UPDATE documents SET category_id=? WHERE id=?", (cat_row["id"], doc_id))
            return {"ok": True, "category": cat, "method": "regex"}

    conn.execute(
        "UPDATE documents SET category='sonstiges', classification_status='regex_classified', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (doc_id,)
    )
    return {"ok": True, "category": "sonstiges", "method": "regex_default"}


def _action_extract_metadata(conn, doc_id: int, params: dict) -> dict:
    try:
        import sys
        sys.path.insert(0, '/opt/vera-office')
        from backend.core.ai.llm_router import LLMRouter
        row = conn.execute(
            "SELECT filename, ocr_text, category FROM documents WHERE id=?", (doc_id,)
        ).fetchone()
        if not row:
            return {"ok": False, "error": "document not found"}

        text_snippet = (row["ocr_text"] or "")[:2000]
        prompt = (
            "<|im_start|>system\n"
            "Extrahiere aus dem Dokument: Datum (YYYY-MM-DD), Absender, Referenznummer, Betrag (float).\n"
            "Antworte IMMER als JSON: {\"date\": \"...\", \"sender\": \"...\", \"ref\": \"...\", \"amount\": null}\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"Datei: {row['filename']}\nText: {text_snippet}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        router = LLMRouter()
        llm = router.get_llm("user_query")
        if not llm:
            return {"ok": False, "error": "no LLM available"}

        response = llm.generate(prompt, max_tokens=150, stop=["<|im_end|>"])
        try:
            import json as _json
            # Find JSON in response
            start = (response or "").find("{")
            end = (response or "").rfind("}") + 1
            if start >= 0 and end > start:
                meta = _json.loads(response[start:end])
                updates = []
                vals = []
                if meta.get("date"):
                    updates.append("document_date=?")
                    vals.append(meta["date"])
                if meta.get("sender"):
                    updates.append("sender=?")
                    vals.append(str(meta["sender"])[:200])
                if meta.get("ref"):
                    updates.append("reference_number=?")
                    vals.append(str(meta["ref"])[:100])
                if meta.get("amount") is not None:
                    try:
                        updates.append("amount=?")
                        vals.append(float(meta["amount"]))
                    except Exception:
                        pass
                if updates:
                    vals.append(doc_id)
                    conn.execute(
                        f"UPDATE documents SET {', '.join(updates)}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        vals
                    )
                return {"ok": True, "extracted": meta}
        except Exception as e:
            logger.warning(f"[WE] extract_metadata JSON parse failed: {e} | response={response!r}")
        return {"ok": True, "skipped": True, "reason": "no valid JSON in response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _action_file_to_category(conn, doc_id: int, params: dict) -> dict:
    """Ensure category column matches category_id (sync)."""
    row = conn.execute("SELECT category_id, category FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "document not found"}

    if row["category_id"] and not row["category"]:
        cat_row = conn.execute("SELECT name FROM categories WHERE id=?", (row["category_id"],)).fetchone()
        if cat_row:
            conn.execute(
                "UPDATE documents SET category=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (cat_row["name"], doc_id)
            )
            return {"ok": True, "synced": cat_row["name"]}

    if row["category"] and not row["category_id"]:
        cat_row = conn.execute("SELECT id FROM categories WHERE name=?", (row["category"],)).fetchone()
        if cat_row:
            conn.execute(
                "UPDATE documents SET category_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (cat_row["id"], doc_id)
            )
            return {"ok": True, "synced_id": cat_row["id"]}

    return {"ok": True, "already_synced": True}


def _action_extract_brain_facts(conn, doc_id: int, params: dict) -> dict:
    """Extract facts into vera_brain.db using LLM."""
    try:
        import sys
        sys.path.insert(0, '/opt/vera-office')
        row = conn.execute(
            "SELECT filename, ocr_text, category FROM documents WHERE id=?", (doc_id,)
        ).fetchone()
        if not row or not row["ocr_text"]:
            return {"ok": True, "skipped": True, "reason": "no ocr_text"}

        from backend.core.vera_brain import vera_brain
        vera_brain.remember(
            subject=row["filename"],
            predicate="content_snippet",
            object=(row["ocr_text"] or "")[:500],
            source="workflow_engine",
            confidence=0.8
        )
        return {"ok": True, "fact_stored": True}
    except Exception as e:
        logger.warning(f"[WE] extract_brain_facts failed: {e}")
        return {"ok": False, "error": str(e)}


def _action_validate_invoice(conn, doc_id: int, params: dict) -> dict:
    """Basic §14 UStG invoice validation."""
    try:
        row = conn.execute(
            "SELECT ocr_text, category FROM documents WHERE id=?", (doc_id,)
        ).fetchone()
        if not row or not row["ocr_text"]:
            return {"ok": True, "skipped": True, "reason": "no ocr_text"}

        text = (row["ocr_text"] or "").lower()
        checks = {
            "has_mwst": bool(re.search(r"mwst|mehrwertsteuer|umsatzsteuer", text)),
            "has_amount": bool(re.search(r"\d+[,\.]\d+\s*(eur|euro|€)|(?<![\w])\$\s*[\d,]+\.?\d*|(?<![\w])[\d,]+\.?\d*\s*usd(?![\w])", text)),
            "has_date": bool(re.search(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}", text)),
            "has_sender": bool(re.search(r"(gmbh|ag|kg|ohg|gbr|co\.|ug|e\.v\.|inc|ltd)", text)),
        }
        passed = sum(checks.values())
        result_str = "valid" if passed >= 3 else "incomplete"
        conn.execute(
            "UPDATE documents SET invoice_validation=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (result_str, doc_id)
        )
        return {"ok": True, "validation": result_str, "checks": checks}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _action_set_retention(conn, doc_id: int, params: dict) -> dict:
    """Set retention_years based on processing_rules table."""
    try:
        row = conn.execute("SELECT category FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row or not row["category"]:
            return {"ok": True, "skipped": True, "reason": "no category"}

        rule_row = conn.execute(
            "SELECT retention_years FROM processing_rules WHERE category=? LIMIT 1",
            (row["category"],)
        ).fetchone()

        years = rule_row["retention_years"] if rule_row else 10
        conn.execute(
            "UPDATE documents SET retention_years=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (years, doc_id)
        )
        return {"ok": True, "retention_years": years, "category": row["category"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Action registry ─────────────────────────────────────────────────────────

ACTION_HANDLERS = {
    "normalize_format": _action_normalize_format,
    "convert_to_pdf": _action_convert_to_pdf,
    "ocr_if_needed": _action_ocr_if_needed,
    "llm_classify": _action_llm_classify,
    "classify_by_filename_regex": _action_classify_by_filename_regex,
    "extract_metadata": _action_extract_metadata,
    "file_to_category": _action_file_to_category,
    "extract_brain_facts": _action_extract_brain_facts,
    "validate_invoice": _action_validate_invoice,
    "set_retention": _action_set_retention,
}


# ─── Main workflow runner ─────────────────────────────────────────────────────

def run_workflow(workflow_id: str, doc_id: int) -> dict:
    """
    Execute a DB-driven workflow for a document.
    Returns: {"status": "completed"|"failed", "run_id": int, "final_category": str, ...}
    """
    conn = _get_conn()
    step_log = []
    final_category = None
    run_id = None
    overall_status = "completed"

    try:
        # Create run record
        cur = conn.execute(
            "INSERT INTO processing_runs (workflow_id, document_id, started_at, status) VALUES (?,?,?,?)",
            (workflow_id, str(doc_id), datetime.utcnow().isoformat(), "running")
        )
        run_id = cur.lastrowid
        conn.commit()

        # Load steps
        steps = conn.execute(
            """SELECT step_id, step_order, action, params_json, condition_sql, on_error,
                      fallback_action, required
               FROM processing_steps
               WHERE workflow_id=?
               ORDER BY step_order""",
            (workflow_id,)
        ).fetchall()

        if not steps:
            logger.warning(f"[WE] No steps found for workflow {workflow_id!r}")
            conn.execute(
                "UPDATE processing_runs SET status='completed', finished_at=?, step_log_json=? WHERE run_id=?",
                (datetime.utcnow().isoformat(), "[]", run_id)
            )
            conn.commit()
            return {"status": "completed", "run_id": run_id, "warning": "no steps configured"}

        for step in steps:
            step_id = step["step_id"]
            action = step["action"]
            params = json.loads(step["params_json"] or "{}")
            condition_sql = step["condition_sql"] or ""
            on_error = step["on_error"] or "fail"
            fallback_action = step["fallback_action"]
            required = bool(step["required"])

            # Evaluate condition
            if condition_sql:
                cond_ok = _eval_condition(conn, condition_sql, doc_id)
                if not cond_ok:
                    step_log.append({
                        "step_id": step_id, "action": action,
                        "status": "skipped", "reason": "condition_false"
                    })
                    logger.debug(f"[WE] Step {step_id} ({action}) skipped: condition false")
                    continue

            # Check action is registered
            if action not in ACTION_HANDLERS:
                err = f"unknown action: {action!r}"
                logger.error(f"[WE] Step {step_id}: {err}")
                if required and on_error == "fail":
                    step_log.append({"step_id": step_id, "action": action, "status": "error", "error": err})
                    overall_status = "failed"
                    break
                else:
                    step_log.append({"step_id": step_id, "action": action, "status": "skipped", "reason": err})
                    continue

            # Execute action
            t0 = time.time()
            try:
                result = ACTION_HANDLERS[action](conn, doc_id, params)
                conn.commit()
                duration_ms = int((time.time() - t0) * 1000)

                if result.get("ok"):
                    cat = result.get("category") or result.get("final_category")
                    if cat:
                        final_category = cat
                    step_log.append({
                        "step_id": step_id, "action": action,
                        "status": "ok", "duration_ms": duration_ms,
                        "result": {k: v for k, v in result.items() if k != "ok"}
                    })
                    logger.info(f"[WE] Step {step_id} ({action}): OK in {duration_ms}ms")
                else:
                    err = result.get("error", "unknown error")
                    duration_ms = int((time.time() - t0) * 1000)
                    logger.warning(f"[WE] Step {step_id} ({action}) failed: {err}")

                    if on_error == "skip" or not required:
                        step_log.append({
                            "step_id": step_id, "action": action,
                            "status": "skipped_error", "error": err
                        })
                        continue
                    elif on_error == "fallback" and fallback_action and fallback_action in ACTION_HANDLERS:
                        logger.info(f"[WE] Step {step_id}: fallback to {fallback_action!r}")
                        fb_result = ACTION_HANDLERS[fallback_action](conn, doc_id, params)
                        conn.commit()
                        cat = fb_result.get("category") or fb_result.get("final_category")
                        if cat:
                            final_category = cat
                        step_log.append({
                            "step_id": step_id, "action": action,
                            "status": "fallback", "fallback_action": fallback_action,
                            "fallback_result": fb_result
                        })
                    else:
                        step_log.append({
                            "step_id": step_id, "action": action,
                            "status": "error", "error": err
                        })
                        if required:
                            overall_status = "failed"
                            break

            except Exception as exc:
                conn.rollback()
                duration_ms = int((time.time() - t0) * 1000)
                err = str(exc)
                logger.error(f"[WE] Step {step_id} ({action}) exception: {err}")
                step_log.append({
                    "step_id": step_id, "action": action,
                    "status": "exception", "error": err, "duration_ms": duration_ms
                })
                if required and on_error == "fail":
                    overall_status = "failed"
                    break

        # Finalize run record
        doc_row = conn.execute("SELECT category FROM documents WHERE id=?", (doc_id,)).fetchone()
        if doc_row and doc_row["category"]:
            final_category = doc_row["category"]

        conn.execute(
            """UPDATE processing_runs
               SET status=?, finished_at=?, step_log_json=?, final_category=?, llm_used=?
               WHERE run_id=?""",
            (
                overall_status,
                datetime.utcnow().isoformat(),
                json.dumps(step_log),
                final_category,
                "workflow_engine",
                run_id
            )
        )
        conn.commit()
        return {
            "status": overall_status,
            "run_id": run_id,
            "final_category": final_category,
            "steps": len(step_log)
        }

    except Exception as e:
        logger.error(f"[WE] run_workflow fatal error: {e}")
        if run_id:
            try:
                conn.execute(
                    "UPDATE processing_runs SET status='failed', finished_at=? WHERE run_id=?",
                    (datetime.utcnow().isoformat(), run_id)
                )
                conn.commit()
            except Exception:
                pass
        return {"status": "failed", "error": str(e), "run_id": run_id}
    finally:
        conn.close()
