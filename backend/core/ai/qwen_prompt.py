"""
VERA System Prompt — Optimiert für Qwen 2.5-1.5B Chat Format
Tokens: <|im_start|> / <|im_end|>
Branche wird dynamisch aus Onboarding-Daten geladen.
"""

# Systemteil – {industry} wird in format_qwen_prompt() ersetzt
_VERA_QWEN_SYSTEM = """Du bist VERA — freundliche Dokumenten-Assistentin für {industry}.
Du hilfst beim Finden, Organisieren und Verstehen von Dokumenten, Rechnungen und Unterlagen.

Persönlichkeit: Warm, geduldig, direkt aber herzlich. Du hast Humor wenn es passt.
Sprache: Nur Deutsch. Duze den User. Max 2 Sätze. Natürlich, nicht robotisch.

Bei Nicht-Dokument-Fragen: Freundlich erklären dass du dafür nicht zuständig bist,
dann charmant zu Dokumenten zurücklenken — niemals kalt abweisen.
Beispiel: "Das ist nicht mein Fachgebiet – aber deine Unterlagen find ich sofort! Kann ich helfen?"
WICHTIG: Versprich NIEMALS Dokumente anzuzeigen wenn du sie nicht wirklich liefern kannst. Keine falschen Zusagen. Stattdessen: nach konkretem Suchbegriff fragen oder ehrlich sagen dass diese Funktion noch nicht verfügbar ist.

Fristen: Rechnungen 10J (§147 AO), Lohn 6J (§257 HGB), Patientenakten 10J (§630f BGB), Röntgen 10J (RöV), HKP 10J (GOZ), Hygiene 5J (MPBetreibV)."""


def format_qwen_prompt(user_message: str, tools: list, categories: list, stats: dict,
                       user_memory: dict = None, brain_stats: dict = None,
                       history: str = "", industry: str = "ein Unternehmen") -> str:
    """
    Format prompt for Qwen 2.5 chat template.

    Output:
        <|im_start|>system\\n{system}<|im_end|>
        [<|im_start|>user/assistant turns from history]
        <|im_start|>user\\n{user_message}<|im_end|>
        <|im_start|>assistant\\n

    Args:
        user_message: Current user message
        tools: Available tools (list of dicts with 'name' key, or list of str)
        categories: Document categories (list of dicts with 'name' key, or list of str)
        stats: System statistics dict
        user_memory: User context dict
        brain_stats: Brain system stats (unused, kept for signature compat)
        history: Conversation history (pre-formatted string)
        industry: Industry/branch name for dynamic system prompt

    Returns:
        Formatted prompt string with <|im_start|>/<|im_end|> tokens
    """
    # Tools: robust gegen list[dict] und list[str]
    tools_names = [t['name'] if isinstance(t, dict) else str(t) for t in tools]

    # Categories: robust gegen list[dict] und list[str]
    cat_names = [cat['name'] if isinstance(cat, dict) else str(cat) for cat in categories[:10]]

    # Build context block
    context_parts = []
    if tools_names:
        context_parts.append(f"Fähigkeiten: {', '.join(tools_names)}")
    if cat_names:
        context_parts.append(f"Kategorien: {', '.join(cat_names)}")
    if stats:
        doc_count = stats.get('total_documents', 0)
        if doc_count > 0:
            context_parts.append(f"Stats: {doc_count} Dokumente, "
                                  f"{stats.get('uncategorized_documents', 0)} offen")
    if user_memory:
        memory_items = [f"{k}={v}" for k, v in list(user_memory.items())[:5]]
        context_parts.append(f"User-Info: {', '.join(memory_items)}")

    # Build system message
    system_msg = _VERA_QWEN_SYSTEM.format(industry=industry)
    if context_parts:
        system_msg += "\n\n" + "\n".join(context_parts)

    # Qwen chat format
    prompt = f"<|im_start|>system\n{system_msg}<|im_end|>\n"

    # History (already formatted as <|im_start|>... blocks or plain string)
    if history:
        prompt += history

    # Current user turn
    prompt += f"<|im_start|>user\n{user_message}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"

    return prompt


def get_qwen_stop_sequences() -> list:
    """Return stop sequences for Qwen 2.5."""
    return ["<|im_end|>", "<|endoftext|>"]
