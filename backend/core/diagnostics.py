"""
VERA Office - Auto-Diagnostics Engine
Erkennt Probleme automatisch und gibt VERA Bescheid
"""
import time
from dataclasses import dataclass
from typing import List, Callable, Optional
from loguru import logger

import psutil


@dataclass
class DiagnosticIssue:
    """Erkanntes Problem"""
    name: str
    severity: str  # "warning" oder "critical"
    user_message: str  # Was VERA dem User sagt
    internal_message: str  # Was ins Log geht


@dataclass
class DiagnosticRule:
    """Diagnose-Regel"""
    name: str
    condition: Callable
    severity: str
    user_message: str
    internal_message: str


class DiagnosticsEngine:
    """
    Auto-Diagnostics für VERA Office
    
    Erkennt Probleme automatisch:
    - OCR-Fehler häufen sich
    - Klassifikations-Konfidenz sinkt
    - Speicherplatz wird knapp
    - Scanner nicht erreichbar
    - Hohe Fehlerrate
    """
    
    def __init__(self, telemetry_service, config):
        self.telemetry = telemetry_service
        self.config = config
        self.enabled = getattr(config, 'DIAGNOSTICS_ENABLED', True)
        
        # Schwellwerte aus Config
        self.ocr_fail_threshold = getattr(config, 'DIAGNOSTICS_OCR_FAIL_THRESHOLD', 3)
        self.confidence_warning_threshold = getattr(config, 'DIAGNOSTICS_CONFIDENCE_WARNING_THRESHOLD', 0.5)
        self.disk_warning_percent = getattr(config, 'DIAGNOSTICS_DISK_WARNING_PERCENT', 90)
        
        # Regeln definieren
        self.rules = self._init_rules()
        
        if self.enabled:
            logger.info("Auto-Diagnostics aktiviert")
    
    def _init_rules(self) -> List[DiagnosticRule]:
        """Initialisiert Diagnose-Regeln"""
        return [
            DiagnosticRule(
                name="ocr_failing",
                condition=lambda: self.consecutive_errors("ocr") >= self.ocr_fail_threshold,
                severity="critical",
                user_message="Ich habe gerade Schwierigkeiten, Dokumente zu lesen. Ich arbeite daran - bitte versuchen Sie es in ein paar Minuten erneut.",
                internal_message="OCR failing consecutively"
            ),
            DiagnosticRule(
                name="low_confidence",
                condition=lambda: self.avg_confidence_last_10() < self.confidence_warning_threshold,
                severity="warning",
                user_message="Mir faellt auf, dass ich bei den letzten Dokumenten unsicher war. Ihre Korrekturen helfen mir, besser zu werden!",
                internal_message="Classification confidence dropping"
            ),
            DiagnosticRule(
                name="disk_full",
                condition=lambda: self.disk_usage_percent() > self.disk_warning_percent,
                severity="critical",
                user_message="Achtung: Der Speicherplatz wird knapp. Bitte kontaktieren Sie Ihren Administrator.",
                internal_message="Disk usage above threshold"
            ),
            DiagnosticRule(
                name="scanner_lost",
                condition=lambda: self.scanner_unreachable_minutes() > 10,
                severity="warning",
                user_message="Ich kann den Scanner nicht mehr finden. Ist er eingeschaltet und im Netzwerk?",
                internal_message="Scanner unreachable for 10+ minutes"
            ),
            DiagnosticRule(
                name="high_error_rate",
                condition=lambda: self.error_rate_last_hour() > 0.3,
                severity="warning",
                user_message="Es treten gerade vermehrt Fehler auf. Ich habe das Problem gemeldet.",
                internal_message="Error rate above 30% in last hour"
            )
        ]
    
    def consecutive_errors(self, action: str) -> int:
        """Anzahl aufeinanderfolgender Fehler für eine Aktion"""
        if not self.telemetry:
            return 0
        return self.telemetry.consecutive_errors.get(action, 0)
    
    def avg_confidence_last_10(self) -> float:
        """Durchschnittliche Konfidenz der letzten 10 Klassifikationen"""
        if not self.telemetry or not self.telemetry.confidence_history:
            return 1.0  # Kein Alarm wenn keine Daten
        return sum(self.telemetry.confidence_history) / len(self.telemetry.confidence_history)
    
    def disk_usage_percent(self) -> float:
        """Aktuelle Festplatten-Auslastung in Prozent"""
        try:
            disk = psutil.disk_usage(str(self.config.DATA_DIR))
            return disk.percent
        except Exception:
            return 0.0
    
    def scanner_unreachable_minutes(self) -> float:
        """Minuten seit letztem Scanner-Kontakt"""
        if not self.telemetry:
            return 0.0
        elapsed = time.time() - self.telemetry.scanner_last_seen
        return elapsed / 60
    
    def error_rate_last_hour(self) -> float:
        """Fehlerrate der letzten Stunde (vereinfacht: seit Start)"""
        if not self.telemetry:
            return 0.0
        
        total_errors = sum(self.telemetry.error_counts.values())
        total_actions = total_errors + self.telemetry.total_documents
        
        if total_actions == 0:
            return 0.0
        
        return total_errors / total_actions
    
    def check_all(self) -> List[DiagnosticIssue]:
        """Prüft alle Regeln und gibt aktive Issues zurück"""
        if not self.enabled:
            return []
        
        issues = []
        
        for rule in self.rules:
            try:
                if rule.condition():
                    issue = DiagnosticIssue(
                        name=rule.name,
                        severity=rule.severity,
                        user_message=rule.user_message,
                        internal_message=rule.internal_message
                    )
                    issues.append(issue)
                    logger.warning(f"Diagnostics Issue: {rule.internal_message}")
            except Exception as e:
                logger.debug(f"Diagnostics-Regel {rule.name} fehlgeschlagen: {e}")
        
        return issues
    
    def get_user_alerts(self) -> List[str]:
        """Gibt User-Nachrichten zurück, die VERA anzeigen soll"""
        issues = self.check_all()
        
        # Nur kritische Issues direkt anzeigen, Warnings zurückhalten
        critical_issues = [i for i in issues if i.severity == "critical"]
        
        return [issue.user_message for issue in critical_issues]
    
    def has_critical_issues(self) -> bool:
        """Prüft ob kritische Issues vorhanden sind"""
        issues = self.check_all()
        return any(i.severity == "critical" for i in issues)
    
    def has_warnings(self) -> bool:
        """Prüft ob Warnungen vorhanden sind"""
        issues = self.check_all()
        return any(i.severity == "warning" for i in issues)


# Globale Instanz (wird in main.py initialisiert)
_diagnostics_engine: Optional[DiagnosticsEngine] = None


def init_diagnostics(telemetry_service, config):
    """Initialisiert globale Diagnostics-Engine"""
    global _diagnostics_engine
    _diagnostics_engine = DiagnosticsEngine(telemetry_service, config)
    return _diagnostics_engine


def get_diagnostics() -> Optional[DiagnosticsEngine]:
    """Gibt globale Diagnostics-Engine zurück"""
    return _diagnostics_engine
