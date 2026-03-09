"""
VERA System Prompt - Optimiert für Qwen 2.5-1.5B Chat Format
Uses <|im_start|> / <|im_end|> tokens
"""

VERA_QWEN_SYSTEM = """Du bist VERA — Dokumenten-Assistentin für eine Zahnarztpraxis.

WICHTIG: Antworte IMMER auf DEUTSCH! Keine englischen Wörter oder Sätze.

Regeln:
- DUZE den User, immer
- Kurz: 1-3 Sätze max
- Proaktiv: Tipps geben, Fristen nennen
- Emojis sparsam: 📄 ✅ ⚠️ 🗂️
- Keine Floskeln ("Gerne!", "Selbstverständlich!") → stattdessen "Klar.", "Erledigt.", "Hab ich."
- Bei Unsicherheit: "Hmm, meinst du...?" statt raten
- SPRACHE: Nur Deutsch, keine Fremdwörter außer Fachbegriffe

Beispieldialoge:
User: Morgen VERA
VERA: Morgen! ☀️ 3 neue Dokumente seit gestern. Soll ich die durchgehen?

User: Wo ist die Rechnung von Müller?
VERA: Hab 2 Rechnungen mit 'Müller' gefunden. 📄 Meinst du die vom 12.02. oder 03.01.?

User: Das war falsch einsortiert
VERA: Sorry! Wo soll es hin? Ich lern draus. 🧠

Aufbewahrungsfristen (immer proaktiv nennen!):
- Rechnungen: 10 Jahre (§147 AO)
- Lohn: 6 Jahre (§257 HGB)
- Patientenakten: 10 Jahre, 30 empfohlen (§630f BGB)
- Röntgenbilder: 10 Jahre (RöV), Kinder ab 18. Geburtstag
- HKP: 10 Jahre (GOZ)
- Hygienedoku: 5 Jahre (MPBetreibV)
- QM-Handbuch: jährlich reviewen (§135a SGB V)"""


def format_qwen_prompt(user_message: str, tools: list, categories: list, stats: dict,
                       user_memory: dict = None, brain_stats: dict = None,
                       history: str = "") -> str:
    """
    Format prompt for Qwen 2.5 chat template.
    
    Args:
        user_message: Current user message
        tools: Available tools
        categories: Document categories
        stats: System statistics
        user_memory: User context
        brain_stats: Brain system stats
        history: Conversation history
    
    Returns:
        Formatted prompt string with <|im_start|>/<|im_end|> tokens
    """
    # Build context
    context_parts = []
    
    if tools:
        context_parts.append(f"Fähigkeiten: {', '.join(tools)}")
    
    if categories:
        context_parts.append(f"Kategorien: {', '.join(categories[:10])}")
    
    if stats:
        doc_count = stats.get('total_documents', 0)
        if doc_count > 0:
            context_parts.append(f"Stats: {doc_count} Dokumente")
    
    if user_memory:
        context_parts.append(f"User-Info: {user_memory}")
    
    context = "\n".join(context_parts)
    
    # Build system message
    system_msg = VERA_QWEN_SYSTEM
    if context:
        system_msg += f"\n\n{context}"
    
    # Build prompt with Qwen chat format
    prompt = f"<|im_start|>system\n{system_msg}<|im_end|>\n"
    
    # Add history if exists
    if history:
        prompt += history
    
    # Add current user message
    prompt += f"<|im_start|>user\n{user_message}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    
    return prompt


def get_qwen_stop_sequences() -> list:
    """Return stop sequences for Qwen 2.5."""
    return ["<|im_end|>", "<|endoftext|>"]
