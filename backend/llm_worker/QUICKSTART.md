# 🚀 VERA LLM Worker - Quick Start

**5-Minuten Setup für VERA Chat Backend**

---

## Step 1: Install Dependencies

```powershell
cd C:\Jarvix\vera-office\backend\llm_worker
py -3.11 -m pip install -r requirements.txt
```

**Time:** ~2 min

---

## Step 2: Start LLM Worker

```powershell
.\start_llm_worker.ps1
```

**Expected Output:**
```
🚀 Starting VERA LLM Worker...
✅ Model found
🔥 Starting LLM Worker on port 18793...
✅ Model loaded successfully in 0.33s
```

**Keep this window open!** (Server is running)

---

## Step 3: Test (New Terminal)

```powershell
cd C:\Jarvix\vera-office\backend\llm_worker
py -3.11 test_worker.py
```

**Expected:**
```
✅ Health check passed
✅ Chat response generated
🎉 ALL TESTS PASSED!
```

---

## Step 4: Start VERA Backend

```powershell
cd C:\Jarvix\vera-office\backend
py -3.11 main.py
```

**VERA Backend now has:**
- `POST /api/chat` - Chat with Mistral 7B
- `GET /api/chat/history` - Get chat history
- `DELETE /api/chat/history` - Clear history

---

## Usage from Frontend (Gwen)

```typescript
// Send message to VERA Chat
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: "Was ist Hygiene-Management?",
    max_tokens: 512
  })
});

const data = await response.json();
console.log(data.response); // AI response in German
```

---

## Troubleshooting

### "Port 18793 already in use"

```powershell
Stop-Process -Name python -Force
```

### "Model not found"

Check:
```powershell
Test-Path "C:\Jarvix\vera-office\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
# Should return: True
```

### "Slow responses (> 20s)"

Normal for CPU-only. For faster inference:
- Add GPU (change `n_gpu_layers=0` to `32` in `server.py`)
- Reduce context window (8192 → 4096)
- Increase CPU threads (8 → 16)

---

## What You Get

✅ **Mistral 7B** running locally (no API costs!)  
✅ **German responses** for dental practice questions  
✅ **Context-aware** (optional RAG integration)  
✅ **Chat history** stored in SQLite  
✅ **REST API** on port 18793  
✅ **Integrated** with VERA Backend  

---

## Next Steps

1. **Connect Gwen** - Implement chat UI that calls `/api/chat`
2. **Add RAG** - Context from QM documents (optional)
3. **Streaming** - Real-time token generation (optional)

---

**Need Help?** Read `LLM_WORKER_SETUP.md` for full documentation.

**Questions?** Check `IMPLEMENTATION_REPORT.md` for details.
