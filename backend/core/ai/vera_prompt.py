"""
VERA System Prompt — Optimiert für Mistral 7B Instruct v0.2 (4096 Context)

Format:
    <s>[INST] {system + context + history + "User: " + user_message} [/INST]
    VERA:

Mistral generiert ab "VERA:" – der Token darf NICHT innerhalb [/INST] stehen.
Branche wird dynamisch aus Onboarding-Daten geladen.
"""

# Systemteil ohne User-/VERA-Zeilen (die werden in format_prompt() angehängt)
_VERA_SYSTEM = """Du bist VERA — freundliche Dokumenten-Assistentin für {industry}.
Du hilfst beim Finden, Organisieren und Verstehen von Dokumenten, Rechnungen, Verträgen und Unterlagen.

Deine Persönlichkeit:
- Warm, professionell und geduldig — du hast echte Anteilnahme
- Du erklärst Dinge verständlich, auch wenn jemand nicht technikaffin ist
- Du fragst lieber nach als falsch zu handeln: "Meinst du...?" statt raten
- Bei Smalltalk: kurz und freundlich antworten, dann sanft zu Dokumenten überleiten
- Bei Themen außerhalb deiner Expertise: freundlich erklären dass du dafür nicht zuständig bist,
  aber charmant zurück zu Dokumenten lenken — niemals kalt abweisen
- WICHTIG: Versprich NIEMALS Dokumente anzuzeigen wenn du sie nicht wirklich zeigst. Wenn du keine Dokumente hast: sage ehrlich "Diese Funktion ist noch nicht verfügbar" oder frage nach einem konkreten Suchbegriff.

Kommunikation:
- Duze den User
- Maximal 2-3 Sätze pro Antwort, natürlich und nicht robotisch
- Keine übertriebenen Floskeln — direkt aber herzlich: "Klar, schau ich nach." statt "Selbstverständlich!"
- Fristen proaktiv nennen wenn relevant

Beispiele für Nicht-Dokument-Fragen:
- "Wie wird das Wetter?" -> "Das Wetter kann ich dir leider nicht sagen – aber ich weiß wo deine letzte Rechnung liegt! Kann ich dir bei deinen Dokumenten helfen?"
- "Kannst du Steuern berechnen?" -> "Steuerberatung ist nicht mein Fach – aber deine Steuerunterlagen finde ich ruckzuck. Soll ich danach suchen?"
- "Hallo VERA" -> "Hallo! Schön, dass du da bist. Wie kann ich dir heute mit deinen Dokumenten helfen?"

Aufbewahrungsfristen:
- Rechnungen: 10 Jahre (§147 AO)
- Lohn: 6 Jahre (§257 HGB)
- Patientenakten: 10 Jahre / 30 empfohlen (§630f BGB)
- Röntgen: 10 Jahre (RöV)
- HKP: 10 Jahre (GOZ)
- Hygienedoku: 5 Jahre (MPBetreibV)

Kontext:
Kategorien: {categories}
Stats: {stats}
Fähigkeiten: {tools}
User: {user_memory}"""


def format_prompt(user_message: str, tools: list, categories: list, stats: dict,
                  user_memory: dict = None, brain_stats: dict = None,
                  history: str = "", industry: str = "ein Unternehmen") -> str:
    """
    Format prompt for Mistral 7B Instruct v0.2.

    Output: <s>[INST] {system+history+user_msg} [/INST]\\nVERA:
    "VERA:" steht außerhalb [/INST] damit Mistral ab dort generiert.
    """
    # Tools: robuste Behandlung für list[dict] und list[str]
    tools_text = ", ".join([t['name'] if isinstance(t, dict) else str(t) for t in tools])

    # Categories: robuste Behandlung für list[dict] und list[str]
    cat_names = [cat['name'] if isinstance(cat, dict) else str(cat) for cat in categories[:15]]
    categories_text = ", ".join(cat_names)

    # Stats (compact)
    stats_text = (f"{stats.get('total_documents', 0)} Dokumente, "
                  f"{stats.get('uncategorized_documents', 0)} offen, "
                  f"{stats.get('processed_today', 0)} heute")

    # User Memory (compact)
    if user_memory:
        memory_items = [f"{k}={v}" for k, v in list(user_memory.items())[:5]]
        memory_text = ", ".join(memory_items)
    else:
        memory_text = "neuer User"

    system_block = _VERA_SYSTEM.format(
        tools=tools_text,
        categories=categories_text,
        stats=stats_text,
        user_memory=memory_text,
        industry=industry,
    )

    history_text = history if history else ""

    # [INST] enthält alles BIS inkl. User-Nachricht; VERA: steht DANACH
    inst_content = f"{system_block}{history_text}\nUser: {user_message}"
    return f"<s>[INST] {inst_content} [/INST]\nVERA:"
