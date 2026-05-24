"""
VERA Agent - Conversational AI Assistant
Handles chat interactions, tool calling, and conversation history
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from backend.core.ai.llm_manager import llm
from backend.core.ai.vera_prompt import format_prompt
from backend.core.ai.qwen_prompt import format_qwen_prompt, get_qwen_stop_sequences
try:
    from backend.core.ai.llm_router import llm_router, TaskType
    _router_available = True
except Exception:
    _router_available = False
from backend.core.ai.onboarding_conversation import OnboardingConversation
from backend.core.ai.brain import brain
from backend.db.database import SessionLocal
from backend.models.document import Document
from backend.models.category import Category
from backend.models.settings import OnboardingState as OnboardingStateModel

logger = logging.getLogger(__name__)


class AgentResponse:
    """Response from VERA agent."""
    
    def __init__(
        self, 
        message: str, 
        actions: Optional[List[Dict]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.message = message
        self.actions = actions or []
        self.suggestions = suggestions or []
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "actions": self.actions,
            "suggestions": self.suggestions
        }


class VERAAgent:
    """VERA conversational agent with tool calling."""
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = {}
        self.onboarding_sessions: Dict[str, OnboardingConversation] = {}
        self.max_history = 10
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict]:
        """Define available tools for VERA."""
        return [
            {
                "name": "search_documents",
                "description": "Suche in Dokumenten nach Stichworten im OCR-Text und Metadaten",
                "parameters": {
                    "query": "Suchbegriff (Text)"
                }
            },
            {
                "name": "classify_document",
                "description": "Dokument neu klassifizieren",
                "parameters": {
                    "doc_id": "Dokument-ID (Zahl)"
                }
            },
            {
                "name": "file_document",
                "description": "Dokument in Kategorie ablegen mit neuem Namen",
                "parameters": {
                    "doc_id": "Dokument-ID",
                    "category": "Kategorie-Name",
                    "name": "Neuer Dateiname"
                }
            },
            {
                "name": "list_documents",
                "description": "Dokumente nach Kategorie oder Zeitraum auflisten",
                "parameters": {
                    "category": "Kategorie-Name (optional)",
                    "date_range": "Zeitraum (optional, z.B. 'letzte_woche', 'dieser_monat')"
                }
            },
            {
                "name": "get_stats",
                "description": "Statistiken über Dokumente abrufen"
            },
            {
                "name": "check_missing",
                "description": "Prüfe fehlende oder erwartete Dokumente"
            }
        ]
    
    def _get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for session."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
    
    def _add_to_history(self, session_id: str, role: str, content: str):
        """Add message to conversation history."""
        history = self._get_conversation_history(session_id)
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last N messages
        if len(history) > self.max_history:
            self.conversations[session_id] = history[-self.max_history:]
    
    def _get_categories(self) -> List[Dict]:
        """Get all document categories."""
        db = SessionLocal()
        try:
            categories = db.query(Category).all()
            return [
                {
                    "name": cat.name,
                    "description": cat.display_name,
                    "retention_years": cat.retention_years
                }
                for cat in categories
            ]
        finally:
            db.close()
    
    def _get_stats(self) -> Dict:
        """Get system statistics."""
        db = SessionLocal()
        try:
            total = db.query(Document).count()
            
            # TEMPORARY FIX: Handle missing classification_status column gracefully
            try:
                categorized = db.query(Document).filter(Document.category_id.isnot(None)).count()
            except Exception as e:
                logger.warning(f"Stats query failed (likely missing column): {e}")
                categorized = 0  # Fallback if column missing
            
            uncategorized = total - categorized
            
            # Heute verarbeitet
            today = datetime.now().date()
            try:
                processed_today = db.query(Document).filter(
                    Document.created_at >= today
                ).count()
            except Exception:
                processed_today = 0  # Fallback
            
            return {
                "total_documents": total,
                "categorized_documents": categorized,
                "uncategorized_documents": uncategorized,
                "processed_today": processed_today
            }
        finally:
            db.close()
    
    def _search_documents(self, query: str) -> List[Dict]:
        """Search documents by query."""
        db = SessionLocal()
        try:
            # Search in OCR text and filename
            docs = db.query(Document).filter(
                (Document.ocr_text.contains(query)) |
                (Document.filename.contains(query))
            ).limit(10).all()
            
            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "category": doc.category.name if doc.category else None,
                    "created_at": doc.created_at.strftime("%Y-%m-%d") if doc.created_at else None
                }
                for doc in docs
            ]
        finally:
            db.close()
    
    def _list_documents(self, category: Optional[str] = None, date_range: Optional[str] = None) -> List[Dict]:
        """List documents by category or date range."""
        db = SessionLocal()
        try:
            query = db.query(Document)
            
            if category:
                cat = db.query(Category).filter(Category.name == category).first()
                if cat:
                    query = query.filter(Document.category_id == cat.id)
            
            # TODO: Implement date_range filtering
            
            docs = query.order_by(Document.created_at.desc()).limit(10).all()
            
            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "category": doc.category.name if doc.category else None,
                    "created_at": doc.created_at.strftime("%Y-%m-%d") if doc.created_at else None
                }
                for doc in docs
            ]
        finally:
            db.close()
    
    def _extract_personal_info(self, user_message: str):
        """Extract and remember personal info from user message."""
        msg_lower = user_message.lower()
        
        # Name extraction
        for prefix in ["ich bin die ", "ich bin der ", "ich bin ", "ich heiße ", "mein name ist "]:
            if prefix in msg_lower:
                name = msg_lower.split(prefix, 1)[1].strip().rstrip(".!?").title()
                if name and len(name) < 30 and " " not in name:
                    brain.remember("name", name, context=f"User sagte: {user_message}")
                    break
        
        # Preferred greeting
        if any(w in msg_lower for w in ["sag nicht", "nenn mich"]):
            for prefix in ["nenn mich "]:
                if prefix in msg_lower:
                    nickname = msg_lower.split(prefix, 1)[1].strip().rstrip(".!?").title()
                    if nickname and len(nickname) < 30:
                        brain.remember("nickname", nickname, context=user_message)
    
    def _build_history_context(self, session_id: str, max_turns: int = 4) -> str:
        """Build conversation history string for LLM context."""
        history = self._get_conversation_history(session_id)
        if not history:
            return ""
        
        recent = history[-(max_turns * 2):]  # Last N turns (user+assistant pairs)
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "VERA"
            lines.append(f"{role}: {msg['content']}")
        
        if lines:
            return "\n\nLetzte Nachrichten:\n" + "\n".join(lines)
        return ""
    
    def _generate_response(self, user_message: str, session_id: str) -> str:
        """Generate response using LLMRouter (Qwen -> Mistral fallback) or templates."""
        categories = self._get_categories()
        stats = self._get_stats()

        # Extract personal info before responding
        self._extract_personal_info(user_message)

        history_context = self._build_history_context(session_id)

        # Try Router first: Qwen (fast) if available, else Mistral (local)
        if _router_available:
            try:
                routed_llm = llm_router.get_llm(TaskType.CHAT)
                if routed_llm and routed_llm.is_available():
                    provider = routed_llm.get_provider_name()
                    if "Qwen" in provider:
                        prompt = format_qwen_prompt(
                            user_message=user_message,
                            tools=self.tools,
                            categories=categories,
                            stats=stats,
                            user_memory=brain.recall_all(),
                            history=history_context,
                        )
                        stop = get_qwen_stop_sequences()
                    else:
                        prompt = format_prompt(
                            user_message=user_message,
                            tools=self.tools,
                            categories=categories,
                            stats=stats,
                            user_memory=brain.recall_all(),
                            brain_stats=brain.get_stats(),
                            history=history_context,
                        )
                        stop = ["</s>", "\n\n\n"]

                    logger.debug(f"Chat via router -> {provider}")
                    response = routed_llm.generate(
                        prompt=prompt, max_tokens=300, temperature=0.7, stop=stop
                    )
                    if response:
                        return response
            except Exception as e:
                logger.warning(f"Router failed, falling back to direct LLM: {e}")

        # Direct fallback: Mistral via LLMManager
        if llm.is_available():
            prompt = format_prompt(
                user_message=user_message,
                tools=self.tools,
                categories=categories,
                stats=stats,
                user_memory=brain.recall_all(),
                brain_stats=brain.get_stats(),
                history=history_context,
            )
            response = llm.generate(prompt=prompt, max_tokens=300, temperature=0.7)
            if response:
                return response

        # Fallback: Template-based responses
        logger.warning("LLM not available - using template responses")
        return self._template_response(user_message, stats)
    
    def _template_response(self, user_message: str, stats: Dict) -> str:
        """Template-based fallback responses — works without LLM."""
        msg_lower = user_message.lower().strip()
        
        # Grüße morgens
        if any(w in msg_lower for w in ["guten morgen", "morgen vera", "morgen!", "moin"]):
            pending = stats.get('uncategorized_documents', 0)
            if pending > 0:
                return f"Morgen!  {pending} Dokument{'e' if pending != 1 else ''} warten auf dich."
            return "Morgen!  Alles aufgeräumt — was steht heute an?"
        
        # Präsenzfragen: "Bist du da?", etc.
        if any(w in msg_lower for w in ["bist du da", "bist du hier", "hörst du mich", "bist du online",
                                         "bist du wach", "bist du bereit", "bist du noch da"]):
            return "Ja, ich bin da!  Was kann ich für dich tun?"

        # Grüße allgemein
        if any(w in msg_lower for w in ["hallo", "hi", "hey", "servus", "guten tag", "tag!"]):
            return "Hey!  Was kann ich für dich tun?"
        
        # Grüße abends / Verabschiedung
        if any(w in msg_lower for w in ["feierabend", "tschüss", "tschüs", "ciao", "bye", "gute nacht", "guten abend"]):
            return "Schönen Feierabend!  Bis morgen."
        
        # Danke
        if any(w in msg_lower for w in ["danke", "dankeschön", "vielen dank", "thx", "merci"]):
            return "Kein Ding!  Noch was?"
        
        # Bitte
        if msg_lower in ["bitte", "ja bitte", "gerne"]:
            return "Erledigt. Was steht als nächstes an?"
        
        # Neueste Dokumente (Bug #695: vorher falsche Versprechen, jetzt echte Daten)
        if any(w in msg_lower for w in ["neueste dokumente", "neuesten dokumente", "neue dokumente", "letzte dokumente", "neueste zeigen", "neues zeigen"]):
            docs = self._list_documents()
            if docs:
                lines = [f"Hier sind die {len(docs)} neuesten Dokumente:"]
                for d in docs[:5]:
                    cat = d.get('category') or 'unkategorisiert'
                    date = d.get('created_at') or ''
                    lines.append(f"  • {d['filename']} ({cat}{', ' + date if date else ''})")
                return "\n".join(lines)
            return "Noch keine Dokumente vorhanden. Du kannst Dokumente über den Upload-Bereich hinzufügen."

        # Suche
        if any(w in msg_lower for w in ["such", "find", "wo ist", "zeig mir", "brauch ich", "wo sind", "hast du"]):
            # Try to extract search term
            for prefix in ["wo ist ", "such ", "find ", "zeig mir ", "ich brauch "]:
                if prefix in msg_lower:
                    query = msg_lower.split(prefix, 1)[1].strip().rstrip("?")
                    if query:
                        results = self._search_documents(query)
                        if results:
                            lines = [f"Hab {len(results)} Treffer gefunden: [DOC]"]
                            for r in results[:5]:
                                lines.append(f"  • {r['filename']} ({r.get('category', 'unkategorisiert')})")
                            return "\n".join(lines)
                        return f"Nichts gefunden für '{query}'. Versuch mal andere Stichwörter?"
            return "Klar! Wonach suchst du? Gib mir ein Stichwort [SEARCH]"
        
        # Ablage
        if any(w in msg_lower for w in ["leg ab", "sortier", "ordne ein", "verschieb", "einsortiern", "ablegen"]):
            return "Klar, wohin soll es? Gib mir die Kategorie oder sag mir was es ist."
        
        # Löschung
        if any(w in msg_lower for w in ["lösch", "entfern", "weg damit", "wegmachen"]):
            return "[WARNING] Vorsicht! Aufbewahrungsfristen beachten. Welches Dokument meinst du?"
        
        # Status / Statistik
        if any(w in msg_lower for w in ["statistik", "übersicht", "wie viele", "was gibt's neues", "status", "was gibt es neues"]):
            t = stats['total_documents']
            u = stats['uncategorized_documents']
            p = stats['processed_today']
            lines = [f"[STATS] Übersicht:"]
            lines.append(f"  • {t} Dokumente gesamt, {stats['categorized_documents']} kategorisiert")
            if u > 0:
                lines.append(f"  • [WARNING] {u} noch unkategorisiert")
            if p > 0:
                lines.append(f"  • {p} heute verarbeitet")
            if u == 0 and t > 0:
                lines.append("  • [OK] Alles aufgeräumt!")
            return "\n".join(lines)
        
        # Hilfe
        if any(w in msg_lower for w in ["hilfe", "help", "was kannst du", "wie geht", "was machst du"]):
            return ("Ich kann: [SEARCH] Dokumente suchen,  Ablegen & sortieren, "
                    "[STATS] Statistiken zeigen, [WARNING] An Fristen erinnern. Was brauchst du?")
        
        # Aufbewahrung
        if any(w in msg_lower for w in ["aufbewahr", "wie lang", "frist", "wann löschen", "aufheben"]):
            return ("Kommt drauf an — Rechnungen 10 Jahre, Lohn 6 Jahre, "
                    "Patientenakten mindestens 10 Jahre. Um welches Dokument geht's?")
        
        # GoBD
        if "gobd" in msg_lower:
            return ("GoBD = Grundsätze ordnungsmäßiger Buchführung. "
                    "Belege müssen unveränderbar, vollständig und nachvollziehbar sein. "
                    "Betrifft v.a. Rechnungen und Kassenbuch.")
        
        # DSGVO
        if "dsgvo" in msg_lower or "datenschutz" in msg_lower:
            return ("DSGVO: Personenbezogene Daten nur so lange wie nötig speichern. "
                    "Einwilligungen dokumentieren, Löschkonzept haben. "
                    "Aber: gesetzliche Aufbewahrungsfristen gehen vor!")
        
        # Fehler / Korrekturen
        if any(w in msg_lower for w in ["falsch", "korrigier", "stimmt nicht", "nein das ist", "verkehrt"]):
            return "Sorry! Was stimmt nicht? Ich lern draus. [BRAIN]"
        
        # Persönliche Info erkennen (Name)
        if any(w in msg_lower for w in ["ich bin ", "ich heiße ", "mein name ist "]):
            for prefix in ["ich bin die ", "ich bin der ", "ich bin ", "ich heiße ", "mein name ist "]:
                if prefix in msg_lower:
                    name = msg_lower.split(prefix, 1)[1].strip().rstrip(".!").title()
                    if name and len(name) < 30:
                        brain.remember("name", name, context=f"User sagte: {user_message}")
                        return f"Freut mich, {name}!  Ich merk mir das."
            return "Freut mich! "
        
        # Ja/Nein
        if msg_lower in ["ja", "jo", "jep", "yes", "genau", "richtig", "stimmt"]:
            return "Alles klar! "
        if msg_lower in ["nein", "ne", "nö", "nope"]:
            return "Ok, kein Problem. Was dann?"
        
        # Unverständlich — freundlich nachfragen
        user_name = brain.recall("name")
        name_suffix = f", {user_name}" if user_name else ""
        return f"Hmm{name_suffix}, das hab ich nicht ganz verstanden. Kannst du das anders formulieren? "
    
    def _is_onboarding_complete(self) -> bool:
        """Check if onboarding is complete."""
        db = SessionLocal()
        try:
            state = db.query(OnboardingStateModel).first()
            return state is not None and state.completed
        finally:
            db.close()
    
    def _get_or_create_onboarding_session(self, session_id: str) -> OnboardingConversation:
        """Get or create onboarding conversation for session."""
        if session_id not in self.onboarding_sessions:
            # Try to load from database
            db = SessionLocal()
            try:
                state = db.query(OnboardingStateModel).first()
                if state and state.onboarding_chat_data:
                    # Resume from saved state
                    self.onboarding_sessions[session_id] = OnboardingConversation.from_dict(
                        state.onboarding_chat_data
                    )
                else:
                    # Create new conversation
                    self.onboarding_sessions[session_id] = OnboardingConversation()
            finally:
                db.close()
        
        return self.onboarding_sessions[session_id]
    
    def _save_onboarding_state(self, session_id: str):
        """Save onboarding conversation state to database."""
        if session_id not in self.onboarding_sessions:
            return
        
        conversation = self.onboarding_sessions[session_id]
        
        db = SessionLocal()
        try:
            state = db.query(OnboardingStateModel).first()
            if not state:
                state = OnboardingStateModel(
                    completed=False,
                    current_step=1,
                    total_steps=5
                )
                db.add(state)
            
            # Save conversation data
            state.onboarding_chat_data = conversation.to_dict()
            db.commit()
        finally:
            db.close()
    
    def _complete_onboarding(self, onboarding_data: Dict):
        """Complete onboarding and create categories."""
        from backend.api.onboarding import (
            CompanyProfile, DocumentType, NetworkConfig,
            OnboardingStep1Request, OnboardingStep2Request, OnboardingStep3Request,
            DOCUMENT_TYPES_BY_INDUSTRY
        )
        from backend.core.ai.filer import filer
        
        db = SessionLocal()
        try:
            state = db.query(OnboardingStateModel).first()
            if not state:
                state = OnboardingStateModel()
                db.add(state)
            
            # Step 1: Company Profile
            company_type = onboarding_data.get("company_type", "")
            industry = onboarding_data.get("industry", "")
            employee_count = onboarding_data.get("employee_count", "")
            
            state.company_profile = {
                "company_type": company_type,
                "industry": industry,
                "employee_range": employee_count
            }
            state.current_step = 2
            
            # Step 2: Document Types
            document_types_names = onboarding_data.get("document_types", [])
            
            # Map display names back to full document type configs
            industry_key = industry if industry in DOCUMENT_TYPES_BY_INDUSTRY else "default"
            all_doc_types = DOCUMENT_TYPES_BY_INDUSTRY.get(industry_key, DOCUMENT_TYPES_BY_INDUSTRY["default"])
            
            # Build document types list
            document_types = []
            for dt_name in document_types_names:
                # Find matching document type config
                for dt in all_doc_types:
                    if dt["display_name"] == dt_name:
                        document_types.append(dt)
                        break
                else:
                    # Custom document type - create basic config
                    safe_name = dt_name.lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                    document_types.append({
                        "name": safe_name,
                        "display_name": dt_name,
                        "storage_path": f"Dokumente/{dt_name}",
                        "retention_years": 10,
                        "keywords": ""
                    })
            
            state.document_types = document_types
            state.current_step = 3
            
            # Create categories in database
            for doc_type in document_types:
                existing = db.query(Category).filter(Category.name == doc_type["name"]).first()
                if not existing:
                    category = Category(
                        name=doc_type["name"],
                        display_name=doc_type["display_name"],
                        storage_path=doc_type["storage_path"],
                        retention_years=doc_type.get("retention_years"),
                        keywords=doc_type.get("keywords", ""),
                        is_system=True
                    )
                    db.add(category)
            
            # Create physical folders
            for doc_type in document_types:
                try:
                    filer.ensure_category_folder(
                        category=doc_type["name"],
                        storage_path=doc_type["storage_path"]
                    )
                except Exception as e:
                    logger.warning(f"Could not create folder for {doc_type['name']}: {e}")
            
            # Step 3: Network
            internet_enabled = onboarding_data.get("internet_enabled", False)
            state.network_config = {
                "internet_enabled": internet_enabled,
                "email_enabled": False
            }
            state.current_step = 4
            
            # Complete
            state.completed = True
            state.completed_at = datetime.utcnow()
            state.current_step = 5
            
            db.commit()
            
            logger.info(f"Onboarding completed: {state.company_profile}")
            
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def chat(self, user_message: str, session_id: str = "default") -> AgentResponse:
        """
        Main chat interface for VERA.
        
        Args:
            user_message: User's message
            session_id: Session identifier for conversation history
        
        Returns:
            AgentResponse with message, actions, and suggestions
        """
        try:
            # Check if onboarding is complete
            if not self._is_onboarding_complete():
                # Handle onboarding conversation
                conversation = self._get_or_create_onboarding_session(session_id)
                result = conversation.process_input(user_message)
                
                # Save state
                self._save_onboarding_state(session_id)
                
                # Check if onboarding is completed
                if result.get("completed", False):
                    # Complete onboarding in database
                    self._complete_onboarding(result["data"])
                    
                    # Clear onboarding session
                    if session_id in self.onboarding_sessions:
                        del self.onboarding_sessions[session_id]
                
                # Return onboarding response
                return AgentResponse(
                    message=result["message"],
                    suggestions=result["suggestions"]
                )
            
            # Normal chat flow
            # Add user message to history
            self._add_to_history(session_id, "user", user_message)
            
            # Generate response
            response_text = self._generate_response(user_message, session_id)
            
            # Add assistant response to history
            self._add_to_history(session_id, "assistant", response_text)
            
            # Generate contextual suggestions
            suggestions = self._generate_suggestions(user_message)
            
            return AgentResponse(
                message=response_text,
                suggestions=suggestions
            )
        
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return AgentResponse(
                message="Entschuldigung, es ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
                suggestions=[]
            )
    
    def _generate_suggestions(self, user_message: str) -> List[str]:
        """Generate contextual suggestions based on user message and time of day."""
        msg_lower = user_message.lower()
        hour = datetime.now().hour
        
        # Context-based suggestions
        if any(w in msg_lower for w in ["such", "find", "wo ist", "zeig"]):
            return ["Erneut suchen", "Filter erweitern", "Letzte Dokumente"]
        
        if any(w in msg_lower for w in ["leg ab", "sortier", "ablage", "verschoben", "einsortiern"]):
            return ["Nächstes Dokument", "Umbenennen", "Kategorie ändern"]
        
        if any(w in msg_lower for w in ["upload", "hochgeladen", "neu", "gescannt"]):
            return ["Klassifizieren", "Umbenennen", "Ordner zuweisen"]
        
        if any(w in msg_lower for w in ["falsch", "korrigier", "stimmt nicht", "nein"]):
            return ["Richtige Kategorie wählen", "Umbenennen", "Nächstes Dokument"]
        
        if any(w in msg_lower for w in ["statistik", "übersicht", "status"]):
            return ["Unkategorisierte zeigen", "Dokument suchen", "Was fehlt?"]
        
        if any(w in msg_lower for w in ["danke", "super", "perfekt"]):
            return ["Noch was suchen?", "Übersicht", "Feierabend! "]
        
        if any(w in msg_lower for w in ["aufbewahr", "frist", "wie lang"]):
            return ["Alle Fristen zeigen", "Ablaufende Dokumente", "GoBD-Info"]
        
        if any(w in msg_lower for w in ["morgen", "hallo", "hey", "servus", "hi"]):
            # Time-based morning suggestions
            if hour < 10:
                return ["Neue Dokumente zeigen", "Was fehlt?", "Übersicht"]
            return ["Dokument suchen", "Was gibt's Neues?", "Statistiken"]
        
        if any(w in msg_lower for w in ["feierabend", "tschüss", "bye"]):
            return ["Offene Dokumente?", "Alles erledigt [OK]", "Bis morgen!"]
        
        # Time-based defaults
        if hour < 9:
            return ["Neue Dokumente", "Was fehlt?", "Übersicht"]
        if hour >= 17:
            return ["Offene Dokumente?", "Statistik", "Feierabend! "]
        
        # Generic defaults
        return ["Dokument suchen", "Was fehlt?", "Übersicht"]


# Global instance
agent = VERAAgent()
