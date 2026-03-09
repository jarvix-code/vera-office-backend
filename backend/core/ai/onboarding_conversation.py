"""
VERA Conversational Onboarding
State machine for natural onboarding conversation
"""
import re
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class OnboardingState(str, Enum):
    """Onboarding conversation states"""
    GREETING = "greeting"
    LANGUAGE = "language"
    COMPANY_NAME = "company_name"
    USER_NAME = "user_name"
    COMPANY_TYPE = "company_type"
    EMPLOYEE_COUNT = "employee_count"
    DOCUMENT_TYPES = "document_types"
    NETWORK = "network"
    COMPLETE = "complete"


class OnboardingConversation:
    """
    Manages conversational onboarding flow.
    Each state has a message, expected input type, validation, and next state.
    """
    
    # Predefined document types by industry
    DOCUMENT_TYPES_BY_INDUSTRY = {
        "Zahnarztpraxis": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Behördenschreiben",
            "QM-Dokumente",
            "Laboraufträge"
        ],
        "Praxis": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Behördenschreiben",
            "QM-Dokumente"
        ],
        "Handwerk": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Behördenschreiben",
            "Angebote"
        ],
        "Büro": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Behördenschreiben",
            "Korrespondenz"
        ],
        "Handel": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Lieferscheine",
            "Bestellungen"
        ],
        "Gastronomie": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Behördenschreiben",
            "Lieferscheine"
        ],
        "default": [
            "Eingangsrechnungen",
            "Ausgangsrechnungen",
            "Personalakten",
            "Verträge",
            "Behördenschreiben"
        ]
    }
    
    # Company type keywords
    COMPANY_TYPE_KEYWORDS = {
        "Praxis": ["praxis", "arzt", "zahnarzt", "tierarzt", "physiotherapie"],
        "Handwerk": ["handwerk", "elektr", "schreiner", "tischler", "maler", "dachdecker", "sanitär", "heizung"],
        "Büro": ["büro", "beratung", "consulting", "agentur", "dienstleist"],
        "Handel": ["handel", "shop", "verkauf", "vertrieb", "groß", "einzel"],
        "Gastronomie": ["gastro", "restaurant", "café", "cafe", "hotel", "pension"],
    }
    
    def __init__(self, session_data: Optional[Dict] = None):
        """
        Initialize onboarding conversation.
        
        Args:
            session_data: Previously saved session data (for resuming)
        """
        self.data = session_data or {}
        self.current_state = OnboardingState(self.data.get("current_state", OnboardingState.GREETING))
    
    def get_message(self) -> str:
        """Get current state message."""
        if self.current_state == OnboardingState.GREETING:
            return (
                "Hallo! Ich bin VERA — Ihre persönliche Assistentin für Dokumentenmanagement.\n\n"
                "Ich spreche Deutsch und helfe Ihnen dabei, den Papierkram endlich in den Griff zu bekommen.\n\n"
                "Damit ich optimal für Sie arbeiten kann, würde ich Sie gerne kurz kennenlernen.\n\n"
                "Wie heißt Ihr Unternehmen?"
            )
        
        elif self.current_state == OnboardingState.LANGUAGE:
            # Optional language selection (currently only German supported)
            return (
                "In welcher Sprache möchten Sie mit mir kommunizieren?\n\n"
                "Verfügbar: Deutsch\n"
                "(Weitere Sprachen sind in Planung)"
            )
        
        elif self.current_state == OnboardingState.COMPANY_NAME:
            # Validation failed - ask again
            return "Bitte geben Sie einen gültigen Unternehmensnamen ein (mindestens 2 Zeichen)."
        
        elif self.current_state == OnboardingState.USER_NAME:
            company_name = self.data.get("company_name", "Ihr Unternehmen")
            return f"Perfekt! Und wie ist Ihr Name?"
        
        elif self.current_state == OnboardingState.COMPANY_TYPE:
            user_name = self.data.get("user_name", "")
            greeting = f"Danke, {user_name}! " if user_name else ""
            company_name = self.data.get("company_name", "Ihr Unternehmen")
            return (
                f"{greeting}Und was für ein Unternehmen ist {company_name}?\n"
                "Zum Beispiel eine Praxis, ein Handwerksbetrieb, ein Büro, oder etwas anderes?"
            )
        
        elif self.current_state == OnboardingState.EMPLOYEE_COUNT:
            company_name = self.data.get("company_name", "Ihr Unternehmen")
            return (
                f"Verstanden! Wie viele Mitarbeiter arbeiten bei {company_name} ungefähr?\n"
                "Das hilft mir, die richtige Dokumentenstruktur vorzuschlagen."
            )
        
        elif self.current_state == OnboardingState.DOCUMENT_TYPES:
            industry = self.data.get("industry", "default")
            employee_count = self.data.get("employee_count", "")
            
            # Get suggested document types
            suggested_types = self._get_suggested_document_types(industry)
            types_list = "\n".join([f"• {dt}" for dt in suggested_types])
            
            # Store suggested types for later reference
            self.data["suggested_document_types"] = suggested_types
            
            return (
                f"Für {industry} mit {employee_count} Mitarbeitern empfehle ich folgende Dokumenttypen:\n\n"
                f"{types_list}\n\n"
                "Soll ich diese so anlegen? Sie können auch welche hinzufügen oder entfernen — "
                "sagen Sie mir einfach Bescheid!"
            )
        
        elif self.current_state == OnboardingState.NETWORK:
            return (
                "Fast geschafft! Noch eine wichtige Frage:\n\n"
                "Soll ich Zugang zum Internet haben?\n"
                "Das brauche ich nur für Software-Updates. "
                "Ihre Dokumente bleiben immer sicher und lokal bei Ihnen."
            )
        
        elif self.current_state == OnboardingState.COMPLETE:
            company_name = self.data.get("company_name", "")
            company_type = self.data.get("company_type", "")
            employee_count = self.data.get("employee_count", "")
            document_types = self.data.get("document_types", [])
            internet = "Ja" if self.data.get("internet_enabled", False) else "Nein"
            
            types_list = ", ".join(document_types[:3])
            if len(document_types) > 3:
                types_list += f" und {len(document_types) - 3} weitere"
            
            return (
                "Perfekt, dann fasse ich zusammen:\n\n"
                f"📋 Unternehmen: {company_name}\n"
                f"🏢 Typ: {company_type}\n"
                f"👥 Mitarbeiter: {employee_count}\n"
                f"📁 Dokumenttypen: {types_list}\n"
                f"🌐 Internet: {internet}\n\n"
                "Stimmt das so? Dann richte ich jetzt alles für Sie ein!"
            )
        
        return "Entschuldigung, da ist etwas schiefgelaufen."
    
    def get_suggestions(self) -> List[str]:
        """Get quick reply suggestions for current state."""
        if self.current_state == OnboardingState.USER_NAME:
            return []  # No suggestions for name input
        
        elif self.current_state == OnboardingState.COMPANY_TYPE:
            return ["Praxis", "Handwerk", "Büro", "Handel", "Gastronomie", "Sonstiges"]
        
        elif self.current_state == OnboardingState.EMPLOYEE_COUNT:
            return ["1-5", "6-20", "21-50", "51-100", "100+"]
        
        elif self.current_state == OnboardingState.DOCUMENT_TYPES:
            return ["So übernehmen", "Noch Laboraufträge hinzufügen", "Ohne Steuerunterlagen"]
        
        elif self.current_state == OnboardingState.NETWORK:
            return ["Ja", "Nein"]
        
        elif self.current_state == OnboardingState.COMPLETE:
            return ["Stimmt!", "Nochmal ändern"]
        
        return []
    
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and advance state.
        
        Args:
            user_input: User's message
        
        Returns:
            Dict with response message, suggestions, and completion status
        """
        user_input = user_input.strip()
        
        # GREETING state: Always show introduction first, then ask for company name
        if self.current_state == OnboardingState.GREETING:
            # Check if this is the very first message in the session
            if not self.data.get("greeting_shown", False):
                # First interaction - show greeting and stay in GREETING state
                self.data["greeting_shown"] = True
                return {
                    "message": self.get_message(),
                    "suggestions": [],
                    "completed": False,
                    "data": self.data
                }
            
            # Second interaction - process company name
            # Extract and validate company name
            company_name = self._parse_company_name(user_input)
            if not self._validate_company_name(company_name):
                # Validation failed - stay in COMPANY_NAME state for retry
                self.current_state = OnboardingState.COMPANY_NAME
            else:
                self.data["company_name"] = company_name
                self.current_state = OnboardingState.USER_NAME
        
        elif self.current_state == OnboardingState.COMPANY_NAME:
            # Retry after validation failure
            company_name = self._parse_company_name(user_input)
            if not self._validate_company_name(company_name):
                # Still invalid - stay in same state
                pass
            else:
                self.data["company_name"] = company_name
                self.current_state = OnboardingState.USER_NAME
        
        elif self.current_state == OnboardingState.USER_NAME:
            # Extract and validate user name
            user_name = self._parse_user_name(user_input)
            if not self._validate_user_name(user_name):
                # Validation failed - ask again
                return {
                    "message": "Bitte geben Sie Ihren Vor- und Nachnamen ein.",
                    "suggestions": [],
                    "completed": False,
                    "data": self.data
                }
            self.data["user_name"] = user_name
            self.current_state = OnboardingState.COMPANY_TYPE
        
        elif self.current_state == OnboardingState.COMPANY_TYPE:
            # Parse company type and industry
            company_type, industry = self._parse_company_type(user_input)
            self.data["company_type"] = company_type
            self.data["industry"] = industry
            self.current_state = OnboardingState.EMPLOYEE_COUNT
        
        elif self.current_state == OnboardingState.EMPLOYEE_COUNT:
            # Parse employee count
            employee_count = self._parse_employee_count(user_input)
            self.data["employee_count"] = employee_count
            self.current_state = OnboardingState.DOCUMENT_TYPES
        
        elif self.current_state == OnboardingState.DOCUMENT_TYPES:
            # Parse document types confirmation/modification
            document_types = self._parse_document_types(user_input)
            self.data["document_types"] = document_types
            self.current_state = OnboardingState.NETWORK
        
        elif self.current_state == OnboardingState.NETWORK:
            # Parse internet permission
            internet_enabled = self._parse_boolean(user_input)
            self.data["internet_enabled"] = internet_enabled
            self.current_state = OnboardingState.COMPLETE
        
        elif self.current_state == OnboardingState.COMPLETE:
            # Check if user confirms or wants to change
            if self._parse_boolean(user_input):
                # User confirmed - onboarding complete
                self.data["confirmed"] = True
                return {
                    "message": "Alles eingerichtet! Willkommen bei VERA Office.\n\nWas kann ich für Sie tun?",
                    "suggestions": ["Dokument suchen", "Was fehlt?", "Letzte Dokumente"],
                    "completed": True,
                    "data": self.data
                }
            else:
                # User wants to change - restart from company name
                self.current_state = OnboardingState.COMPANY_NAME
        
        # Update session data
        self.data["current_state"] = self.current_state.value
        
        # Return response
        return {
            "message": self.get_message(),
            "suggestions": self.get_suggestions(),
            "completed": False,
            "data": self.data
        }
    
    def _validate_company_name(self, company_name: str) -> bool:
        """
        Validate company name.
        
        Rules:
        - At least 2 characters
        - No greetings like "Hallo", "Hi", "Hey"
        - No single-word common words
        """
        if not company_name or len(company_name) < 2:
            return False
        
        # Block greeting words
        greeting_words = ["hallo", "hi", "hey", "servus", "moin", "tach", "grüß", "guten tag", 
                         "guten morgen", "guten abend", "gute nacht", "tag", "morgen", "abend"]
        name_lower = company_name.lower().strip()
        
        if name_lower in greeting_words:
            return False
        
        # Block other common non-company words
        blocked_words = ["ja", "nein", "ok", "okay", "danke", "bitte", "test", "firma", "unternehmen"]
        if name_lower in blocked_words:
            return False
        
        return True
    
    def _parse_company_name(self, text: str) -> str:
        """Extract company name from user input."""
        # Remove common prefixes
        text = re.sub(r'^(ich heiße|heißt|der name ist|wir heißen|firma|unternehmen|das ist|wir sind)\s+', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def _validate_user_name(self, user_name: str) -> bool:
        """
        Validate user name.
        
        Rules:
        - At least 2 words (first name + last name)
        - No greetings or common filler words
        """
        if not user_name or len(user_name) < 3:
            return False
        
        # Must have at least 2 words (first + last name)
        words = user_name.split()
        if len(words) < 2:
            return False
        
        # Block greeting words
        greeting_words = ["hallo", "hi", "hey", "servus", "moin"]
        name_lower = user_name.lower().strip()
        
        for greeting in greeting_words:
            if greeting in name_lower:
                return False
        
        return True
    
    def _parse_user_name(self, text: str) -> str:
        """Extract user name from user input."""
        # Remove common prefixes
        text = re.sub(r'^(ich bin|ich heiße|heißt|mein name ist|ich bin die|ich bin der|meine name ist)\s+', '', text, flags=re.IGNORECASE)
        
        # Title case
        return text.strip().title()
    
    def _parse_company_type(self, text: str) -> tuple[str, str]:
        """
        Parse company type and derive industry.
        
        Returns:
            Tuple of (company_type, industry)
        """
        text_lower = text.lower()
        
        # Check for keywords
        for company_type, keywords in self.COMPANY_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Derive industry
                    if "zahnarzt" in text_lower:
                        industry = "Zahnarztpraxis"
                    elif "tierarzt" in text_lower:
                        industry = "Tierarztpraxis"
                    elif "arzt" in text_lower or "praxis" in text_lower:
                        industry = "Praxis"
                    else:
                        industry = company_type
                    
                    return company_type, industry
        
        # Default: use user input as both type and industry
        clean_text = re.sub(r'^(ein|eine|der|die|das)\s+', '', text, flags=re.IGNORECASE).strip()
        return clean_text, clean_text
    
    def _parse_employee_count(self, text: str) -> str:
        """Parse employee count from user input."""
        # Extract numbers
        numbers = re.findall(r'\d+', text)
        if numbers:
            count = int(numbers[0])
            # Normalize to ranges
            if count <= 5:
                return "1-5"
            elif count <= 20:
                return "6-20"
            elif count <= 50:
                return "21-50"
            elif count <= 100:
                return "51-100"
            else:
                return "100+"
        
        # Check for range patterns
        if "1-5" in text or "1 bis 5" in text:
            return "1-5"
        elif "6-20" in text or "6 bis 20" in text:
            return "6-20"
        elif "21-50" in text or "21 bis 50" in text:
            return "21-50"
        elif "51-100" in text or "51 bis 100" in text:
            return "51-100"
        elif "100+" in text or "über 100" in text or "mehr als 100" in text:
            return "100+"
        
        # Default
        return text.strip()
    
    def _parse_document_types(self, text: str) -> List[str]:
        """Parse document types confirmation and modifications."""
        text_lower = text.lower()
        
        # Get suggested types
        suggested_types = self.data.get("suggested_document_types", [])
        document_types = suggested_types.copy()
        
        # Check for confirmation keywords
        if any(word in text_lower for word in ["ja", "ok", "passt", "übernehmen", "stimmt", "genau", "klar"]):
            # Check for additions
            if "labor" in text_lower and "Laboraufträge" not in document_types:
                document_types.append("Laboraufträge")
            if "steuer" in text_lower and "hinzu" in text_lower and "Steuerunterlagen" not in document_types:
                document_types.append("Steuerunterlagen")
            
            # Check for removals
            if "ohne" in text_lower or "nicht" in text_lower or "kein" in text_lower:
                if "steuer" in text_lower:
                    document_types = [dt for dt in document_types if "Steuer" not in dt]
                if "labor" in text_lower:
                    document_types = [dt for dt in document_types if "Labor" not in dt]
        
        return document_types
    
    def _parse_boolean(self, text: str) -> bool:
        """Parse yes/no from user input."""
        text_lower = text.lower()
        
        # Positive keywords
        if any(word in text_lower for word in ["ja", "yes", "klar", "ok", "gerne", "stimmt", "genau", "richtig"]):
            return True
        
        # Negative keywords
        if any(word in text_lower for word in ["nein", "ne", "nee", "no", "nicht", "ohne"]):
            return False
        
        # Default to true
        return True
    
    def _get_suggested_document_types(self, industry: str) -> List[str]:
        """Get suggested document types based on industry."""
        # Try exact match
        if industry in self.DOCUMENT_TYPES_BY_INDUSTRY:
            return self.DOCUMENT_TYPES_BY_INDUSTRY[industry].copy()
        
        # Try partial match
        for key in self.DOCUMENT_TYPES_BY_INDUSTRY.keys():
            if key.lower() in industry.lower() or industry.lower() in key.lower():
                return self.DOCUMENT_TYPES_BY_INDUSTRY[key].copy()
        
        # Default
        return self.DOCUMENT_TYPES_BY_INDUSTRY["default"].copy()
    
    def to_dict(self) -> Dict:
        """Export conversation state to dict."""
        return {
            "current_state": self.current_state.value,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OnboardingConversation":
        """Create conversation from dict."""
        return cls(session_data=data.get("data", {}))
