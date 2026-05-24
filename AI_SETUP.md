# AI Setup Guide - llama-cpp-python Installation

## Problem
`llama-cpp-python` benötigt einen C++ Compiler zum Builden. Auf Windows ohne Visual Studio Build Tools schlägt die Installation fehl.

## Lösungen

### Option 1: Pre-built Wheel (empfohlen)
Warte auf verfügbare Wheels oder nutze:
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

Falls das nicht funktioniert, probiere:
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121  # CUDA 12.1
```

### Option 2: Visual Studio Build Tools installieren
1. Installiere [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
2. Wähle "Desktop Development with C++"
3. Danach: `pip install llama-cpp-python`

### Option 3: Ohne LLM laufen lassen
Der Code ist so geschrieben dass VERA Office auch ohne AI läuft (graceful degradation):
- Klassifikation wird übersprungen
- Manuelle Kategorisierung ist weiterhin möglich
- Alle anderen Features funktionieren normal

## Model Download

**WICHTIG:** Download via Browser empfohlen (PowerShell hatte Auth-Probleme mit HuggingFace).

### Schritt 1: Manueller Download
1. Öffne im Browser: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF
2. Scrolle zu "Files and versions"
3. Download: `mistral-7b-instruct-v0.3.Q4_K_M.gguf` (~4.4 GB)
4. Verschiebe nach: `C:\Jarvix\vera-office\models\`

### Schritt 2: Verify
```bash
# Sollte die Datei zeigen (~4.4 GB):
dir C:\Jarvix\vera-office\models\
```

### Alternative: wget/curl (wenn installiert)
```bash
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/mistral-7b-instruct-v0.3.Q4_K_M.gguf -O C:\Jarvix\vera-office\models\mistral-7b-instruct-v0.3.Q4_K_M.gguf
```

## Check Installation

```python
from backend.core.ai.llm_manager import llm

print(f"LLM available: {llm.is_available()}")
```

Sollte `True` ausgeben wenn alles funktioniert.

## Status beim letzten Build
- ❌ llama-cpp-python Installation fehlgeschlagen (kein C++ Compiler)
- ⏳ Model-Download läuft im Hintergrund
- ✅ Alle anderen Dependencies installiert (zeroconf, scikit-learn)
- ✅ Code ist bereit (läuft ohne LLM mit Fallback)
