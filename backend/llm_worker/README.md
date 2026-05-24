# 🤖 VERA LLM Worker

**Local Mistral 7B Backend für VERA Chat (Gwen Interface)**

---

## Quick Start

### 1️⃣ Install Dependencies

```powershell
cd C:\Jarvix\vera-office\backend\llm_worker
py -3.11 -m pip install -r requirements.txt
```

### 2️⃣ Start LLM Worker

```powershell
.\start_llm_worker.ps1
```

**Expected Output:**
```
🚀 Starting VERA LLM Worker...
✅ Model found: C:\Jarvix\vera-office\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf
🔥 Starting LLM Worker on port 18793...
   Model: Mistral 7B Instruct v0.2
   Context Window: 8192 tokens
   CPU Threads: 8
```

### 3️⃣ Test the Worker

```powershell
py -3.11 test_worker.py
```

**Should see:**
```
✅ Health check passed
✅ Chat response generated
✅ Average response time: ~2000ms
🎉 ALL TESTS PASSED! 🎉
```

---

## Architecture

```
User → Gwen (Frontend Chat) 
  ↓
POST /api/chat (VERA Backend)
  ↓
POST http://127.0.0.1:18793/chat (LLM Worker)
  ↓
Mistral 7B (llama-cpp-python)
  ↓
Response → VERA Backend → Gwen → User
```

---

## Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI server (port 18793) |
| `start_llm_worker.ps1` | Windows startup script |
| `start_llm_worker.sh` | Linux startup script |
| `llm_worker.service` | Systemd service (auto-start) |
| `test_worker.py` | Test suite |
| `requirements.txt` | Python dependencies |
| `LLM_WORKER_SETUP.md` | Full documentation |

---

## API Endpoints

- `GET /health` - Health check
- `GET /models` - List available models
- `POST /chat` - Generate chat response
- `GET /` - API info

---

## Integration Status

✅ **COMPLETED:**
- [x] LLM Worker server (`server.py`)
- [x] VERA Chat API (`backend/api/vera_chat.py`)
- [x] Chat DB model (`backend/models/chat.py`)
- [x] Router registered in `main.py`
- [x] Chat DB initialized on startup
- [x] Startup scripts (Windows + Linux)
- [x] Systemd service
- [x] Test suite
- [x] Documentation

⏳ **TODO (Optional):**
- [ ] RAG Integration (context from QM documents)
- [ ] Streaming responses (SSE)
- [ ] Frontend Integration (Gwen Chat UI)

---

## Troubleshooting

### Port already in use

```powershell
Stop-Process -Name python -Force
```

### Slow responses (> 5s)

Increase CPU threads in `server.py`:

```python
CPU_THREADS = 16  # Increase from 8 to 16
```

### Model not found

Check model path:

```powershell
Test-Path "C:\Jarvix\vera-office\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

---

## Next Steps

1. **Test LLM Worker:** Run `test_worker.py` ✅
2. **Start VERA Backend:** Backend should now have `/api/chat` endpoint
3. **Connect Gwen:** Frontend can now call `/api/chat` for AI responses
4. **Optional:** Implement RAG for context-aware answers

---

**Created:** 2026-03-28  
**Version:** 1.0.0  
**Status:** Production-Ready ✅
