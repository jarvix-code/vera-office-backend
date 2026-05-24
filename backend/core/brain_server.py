#!/usr/bin/env python3
"""
Brain Server — Persistent Model-Cache Server for Javix Brain

Loads the sentence-transformers model ONCE at startup and keeps it in RAM.
HTTP API on localhost:18790 for fast recall/capture/context operations.

Endpoints:
    POST /recall   — {"message": "...", "top_k": 5}
    POST /capture  — {"conversation": [...]}
    POST /context  — {"message": "...", "max_tokens": 4000}
    GET  /status   — Full module status
    GET  /health   — Quick healthcheck
    POST /shutdown — Graceful shutdown

    Skills:
    GET  /skills          — List all skills
    POST /skills/execute  — {"skill_id": "...", "params": {...}}
    POST /skills/reload   — {"skill_id": "..."} or {} for all

    Scheduler:
    GET  /scheduler/tasks      — List all scheduled tasks
    POST /scheduler/add        — {"name": "...", "cron": "...", "task": "..."}
    POST /scheduler/remove     — {"task_id": "..."}
    POST /scheduler/enable     — {"task_id": "...", "enabled": true/false}

    Sandbox:
    POST /sandbox/execute — {"code": "...", "language": "python", "timeout": 30}
"""

import json
import signal
import sys
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Event
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Add src dir to path
SRC_DIR = Path(__file__).parent
sys.path.insert(0, str(SRC_DIR))

HOST = "127.0.0.1"
PORT = 18790
LLM_WORKER_URL = "http://127.0.0.1:18793"
LLM_WORKER_API_KEY = "openclaw-llm-worker-secret-2026"

# Global references (set after model load)
_brain_engine = None
_auto_recall = None
_orchestrator = None
_start_time = None
_shutdown_event = Event()


def _get_brain_engine():
    """Lazy-load BrainEngine (holds the heavy model)."""
    global _brain_engine
    if _brain_engine is None:
        from brain_engine import BrainEngine
        _brain_engine = BrainEngine()
    return _brain_engine


def _get_auto_recall():
    """Lazy-load AutoRecall."""
    global _auto_recall
    if _auto_recall is None:
        from auto_recall import AutoRecall
        _auto_recall = AutoRecall(brain=_get_brain_engine())
    return _auto_recall


def _get_orchestrator():
    """Lazy-load BrainOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        from brain_orchestrator import BrainOrchestrator
        _orchestrator = BrainOrchestrator(lazy=True)
        # Inject already-loaded brain engine to avoid double model load
        if _brain_engine is not None:
            _orchestrator._modules['brain_engine'] = _brain_engine
    return _orchestrator


class BrainRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for brain operations."""

    def log_message(self, format, *args):
        """Override to add timestamp."""
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {format % args}\n")
        sys.stderr.flush()

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    #  GET endpoints 

    def do_GET(self):
        try:
            if self.path == "/health":
                self._handle_health()
            elif self.path == "/status":
                self._handle_status()
            elif self.path == "/skills":
                self._handle_skills_list()
            elif self.path == "/scheduler/tasks":
                self._handle_scheduler_list()
            elif self.path == "/brain/v2/status":
                self._handle_brain_v2_status()
            elif self.path == "/brain/v2/tasks":
                self._handle_brain_v2_tasks()
            elif self.path.startswith("/brain/v2/profile"):
                self._handle_brain_v2_profile_get()
            else:
                self._send_json({"error": f"Unknown endpoint: {self.path}"}, 404)
        except Exception as e:
            self._send_json({"error": str(e), "traceback": traceback.format_exc()}, 500)

    #  POST endpoints 

    def do_POST(self):
        try:
            if self.path == "/recall":
                self._handle_recall()
            elif self.path == "/capture":
                self._handle_capture()
            elif self.path == "/context":
                self._handle_context()
            elif self.path == "/prefilter":
                self._handle_prefilter()
            elif self.path == "/permission/check":
                self._handle_permission_check()
            elif self.path == "/permission/respond":
                self._handle_permission_respond()
            elif self.path == "/skills/execute":
                self._handle_skill_execute()
            elif self.path == "/skills/reload":
                self._handle_skill_reload()
            elif self.path == "/scheduler/add":
                self._handle_scheduler_add()
            elif self.path == "/scheduler/remove":
                self._handle_scheduler_remove()
            elif self.path == "/scheduler/enable":
                self._handle_scheduler_enable()
            elif self.path == "/sandbox/execute":
                self._handle_sandbox_execute()
            elif self.path == "/brain/v2/recall":
                self._handle_brain_v2_recall()
            elif self.path == "/brain/v2/profile":
                self._handle_brain_v2_profile_update()
            elif self.path == "/brain/v2/task/start":
                self._handle_brain_v2_task_start()
            elif self.path == "/brain/v2/task/update":
                self._handle_brain_v2_task_update()
            elif self.path == "/brain/v2/task/complete":
                self._handle_brain_v2_task_complete()
            elif self.path == "/shutdown":
                self._handle_shutdown()
            else:
                self._send_json({"error": f"Unknown endpoint: {self.path}"}, 404)
        except Exception as e:
            self._send_json({"error": str(e), "traceback": traceback.format_exc()}, 500)

    #  Handlers 

    def _handle_health(self):
        uptime = round(time.time() - _start_time) if _start_time else 0
        self._send_json({
            "status": "ok",
            "uptime_seconds": uptime,
            "model_loaded": _brain_engine is not None,
            "port": PORT
        })

    def _handle_status(self):
        t0 = time.time()
        try:
            orch = _get_orchestrator()
            status = orch.get_status()
            status["success"] = True
        except Exception as e:
            status = {"success": False, "error": str(e)}
        status["duration_ms"] = round((time.time() - t0) * 1000)
        self._send_json(status)

    def _handle_recall(self):
        t0 = time.time()
        body = self._read_json()
        message = body.get("message", "")
        top_k = body.get("top_k", 3)       # Default 3 (was 5)
        max_tokens = body.get("max_tokens", 1000)  # Token budget

        if not message:
            self._send_json({"error": "Missing 'message' field"}, 400)
            return

        recall = _get_auto_recall()
        should = recall.should_recall(message)

        context = ""
        token_count = 0
        if should:
            brain = _get_brain_engine()
            memories = brain.search_with_budget(message, max_tokens=max_tokens, top_k=top_k * 3)
            if memories:
                context = recall.recall(message, top_k=len(memories))
                token_count = len(context) // 4

        self._send_json({
            "command": "recall",
            "message": message,
            "should_recall": should,
            "context": context,
            "token_count": token_count,
            "success": True,
            "duration_ms": round((time.time() - t0) * 1000)
        })

    def _handle_capture(self):
        t0 = time.time()
        body = self._read_json()
        conversation = body.get("conversation", [])

        if isinstance(conversation, str):
            try:
                conversation = json.loads(conversation)
            except json.JSONDecodeError:
                conversation = [{"role": "user", "content": conversation}]

        if not conversation:
            self._send_json({"error": "Missing 'conversation' field"}, 400)
            return

        orch = _get_orchestrator()
        try:
            result = orch.post_conversation(conversation)

            # Auto-Extract personal memories (LobsterAI-style)
            auto_extracted = 0
            try:
                from memory_extractor import MemoryExtractor
                extractor = MemoryExtractor(_get_brain_engine())
                memories = extractor.extract_from_conversation(conversation)
                if memories:
                    auto_extracted = extractor.store_memories(memories)
            except Exception as ex:
                sys.stderr.write(f"[WARN] Memory extraction failed: {ex}\n")

            self._send_json({
                "command": "capture",
                "success": True,
                "captured": result.get("captured", 0),
                "auto_extracted": auto_extracted,
                "checkpoint": result.get("checkpoint", False),
                "lessons": result.get("lessons", []),
                "duration_ms": round((time.time() - t0) * 1000)
            })
        except Exception as e:
            self._send_json({
                "command": "capture",
                "success": False,
                "error": str(e),
                "duration_ms": round((time.time() - t0) * 1000)
            }, 500)

    def _handle_context(self):
        t0 = time.time()
        body = self._read_json()
        message = body.get("message", "")
        max_tokens = body.get("max_tokens", 4000)

        if not message:
            self._send_json({"error": "Missing 'message' field"}, 400)
            return

        orch = _get_orchestrator()
        ctx = orch.get_context(message, max_tokens)

        self._send_json({
            "command": "context",
            "message": message,
            "context": ctx,
            "success": True,
            "duration_ms": round((time.time() - t0) * 1000)
        })

    def _handle_prefilter(self):
        t0 = time.time()
        body = self._read_json()
        message = body.get("message", "")

        if not message:
            self._send_json({"error": "Missing 'message' field"}, 400)
            return

        # Step 1: Check if LLM worker is available
        llm_available = self._check_llm_worker()
        if not llm_available:
            self._send_json({
                "can_handle": False,
                "response": "",
                "confidence": 0.0,
                "reason": "LLM worker not available",
                "duration_ms": round((time.time() - t0) * 1000)
            })
            return

        # Step 2: Do semantic recall to get context
        recall = _get_auto_recall()
        should_recall, context = recall.recall_with_decision(message, top_k=5)

        # Step 3: Determine if this is a simple question
        is_simple = self._is_simple_question(message)

        if not is_simple:
            self._send_json({
                "can_handle": False,
                "response": "",
                "confidence": 0.0,
                "reason": "Question is too complex (requires coding, analysis, or decisions)",
                "duration_ms": round((time.time() - t0) * 1000)
            })
            return

        # Step 4: Query LLM worker with message + context
        llm_response = self._query_llm_worker(message, context if should_recall else "")

        if llm_response is None:
            self._send_json({
                "can_handle": False,
                "response": "",
                "confidence": 0.0,
                "reason": "LLM worker failed to respond",
                "duration_ms": round((time.time() - t0) * 1000)
            })
            return

        # Step 5: Evaluate confidence
        confidence = self._evaluate_confidence(message, context, llm_response)

        can_handle = confidence > 0.7 and should_recall

        self._send_json({
            "can_handle": can_handle,
            "response": llm_response if can_handle else "",
            "confidence": confidence,
            "has_context": should_recall,
            "duration_ms": round((time.time() - t0) * 1000)
        })

    def _check_llm_worker(self) -> bool:
        """Check if LLM worker is available."""
        try:
            req = Request(f"{LLM_WORKER_URL}/health")
            with urlopen(req, timeout=2) as response:
                return response.status == 200
        except (URLError, HTTPError):
            return False

    def _is_simple_question(self, message: str) -> bool:
        """Determine if message is a simple question (not coding/analysis/decision)."""
        message_lower = message.lower()

        # Complex indicators - if any of these are present, it's NOT simple
        complex_indicators = [
            "implement", "code", "function", "class", "fix bug", "refactor",
            "analyze", "debug", "optimize", "design", "architecture",
            "should i", "what should", "how to implement", "create", "build",
            "modify", "change the code", "add feature", "write"
        ]

        for indicator in complex_indicators:
            if indicator in message_lower:
                return False

        # Simple indicators - factual questions, status checks
        simple_indicators = [
            "what is", "who is", "when", "where", "status", "explain",
            "tell me about", "describe", "what does", "meaning of",
            "definition", "how does", "why does"
        ]

        for indicator in simple_indicators:
            if indicator in message_lower:
                return True

        # Default: if message is a question and short, likely simple
        return "?" in message and len(message.split()) < 20

    def _query_llm_worker(self, message: str, context: str) -> str:
        """Query LLM worker for answer."""
        try:
            # Build prompt with context
            if context:
                prompt = f"""Based on the following context, answer the question concisely.

Context:
{context}

Question: {message}

Answer:"""
            else:
                prompt = f"Question: {message}\n\nAnswer:"

            # Use summarization task as it's the simplest
            payload = {
                "task": "summarize",
                "params": {
                    "text": prompt,
                    "max_length": 200
                }
            }

            # Prepare request with urllib
            payload_bytes = json.dumps(payload).encode("utf-8")
            req = Request(
                f"{LLM_WORKER_URL}/task",
                data=payload_bytes,
                headers={
                    "X-API-Key": LLM_WORKER_API_KEY,
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            with urlopen(req, timeout=30) as response:
                if response.status != 200:
                    return None
                
                result_bytes = response.read()
                result = json.loads(result_bytes.decode("utf-8"))
                return result.get("result", {}).get("summary", "")

        except (URLError, HTTPError, json.JSONDecodeError) as e:
            sys.stderr.write(f"[ERROR] LLM worker query failed: {e}\n")
            return None

    def _evaluate_confidence(self, message: str, context: str, response: str) -> float:
        """Evaluate confidence in the LLM response."""
        confidence = 0.5  # Base confidence

        # Higher confidence if we had context
        if context and len(context) > 100:
            confidence += 0.2

        # Higher confidence if response is substantial
        if response and len(response) > 50:
            confidence += 0.1

        # Lower confidence if response is too short or vague
        if not response or len(response) < 20:
            confidence -= 0.3

        # Lower confidence if response contains uncertainty markers
        uncertainty_markers = ["not sure", "maybe", "possibly", "unclear", "don't know"]
        if any(marker in response.lower() for marker in uncertainty_markers):
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _handle_permission_check(self):
        """POST /permission/check - Check if tool needs approval."""
        body = self._read_json()
        tool = body.get("tool", "")
        params = body.get("params", {})

        if not tool:
            self._send_json({"error": "Missing 'tool' field"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "security"))
            from permission_gating import get_gating
            gating = get_gating()

            needs_approval = gating.should_request_approval(tool, params)
            risk = gating.assess_risk(tool, params).value

            result = {"needs_approval": needs_approval, "risk": risk, "success": True}

            if needs_approval:
                request = gating.create_approval_request(tool, params)
                result["request"] = request

            self._send_json(result)

        except Exception as e:
            self._send_json({"needs_approval": False, "risk": "unknown", "error": str(e)})

    def _handle_permission_respond(self):
        """POST /permission/respond - Handle user approval/denial."""
        body = self._read_json()
        request_id = body.get("request_id", "")
        action = body.get("action", "")

        if not request_id or not action:
            self._send_json({"error": "Missing request_id or action"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "security"))
            from permission_gating import get_gating
            gating = get_gating()

            approved = gating.handle_response(request_id, action)
            self._send_json({"approved": approved, "request_id": request_id, "success": True})

        except Exception as e:
            self._send_json({"approved": False, "error": str(e)})

    #  Skill Handlers 

    def _handle_skills_list(self):
        """GET /skills - List all available skills."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills"))
            from skill_manager import get_skill_manager
            manager = get_skill_manager()
            self._send_json({"success": True, **manager.to_dict()})
        except Exception as e:
            self._send_json({"success": False, "error": str(e), "skills": []})

    def _handle_skill_execute(self):
        """POST /skills/execute - Execute a skill."""
        body = self._read_json()
        skill_id = body.get("skill_id", "")
        params = body.get("params", {})

        if not skill_id:
            self._send_json({"error": "Missing 'skill_id' field"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills"))
            from skill_manager import get_skill_manager
            manager = get_skill_manager()
            result = manager.execute_skill(skill_id, params)
            self._send_json(result)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_skill_reload(self):
        """POST /skills/reload - Reload skill(s)."""
        body = self._read_json()
        skill_id = body.get("skill_id", "")

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills"))
            from skill_manager import get_skill_manager
            manager = get_skill_manager()

            if skill_id:
                success = manager.reload_skill(skill_id)
                self._send_json({"success": success, "skill_id": skill_id})
            else:
                manager.reload_all()
                self._send_json({"success": True, "reloaded": "all"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    #  Scheduler Handlers 

    def _handle_scheduler_list(self):
        """GET /scheduler/tasks - List all scheduled tasks."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scheduler"))
            from task_scheduler import get_scheduler
            scheduler = get_scheduler()
            self._send_json({"success": True, **scheduler.to_dict()})
        except Exception as e:
            self._send_json({"success": False, "error": str(e), "tasks": []})

    def _handle_scheduler_add(self):
        """POST /scheduler/add - Add a scheduled task."""
        body = self._read_json()
        name = body.get("name", "")
        cron = body.get("cron", "")
        task = body.get("task", "")
        natural_language = body.get("natural_language", "")

        if not name or not task:
            self._send_json({"error": "Missing 'name' or 'task' field"}, 400)
            return

        if not cron and not natural_language:
            self._send_json({"error": "Missing 'cron' or 'natural_language' field"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scheduler"))
            from task_scheduler import get_scheduler
            scheduler = get_scheduler()

            task_id = scheduler.add_task(
                name=name,
                cron_expression=cron or "0 * * * *",
                task=task,
                natural_language=natural_language or None,
            )
            self._send_json({"success": True, "task_id": task_id})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_scheduler_remove(self):
        """POST /scheduler/remove - Remove a scheduled task."""
        body = self._read_json()
        task_id = body.get("task_id", "")

        if not task_id:
            self._send_json({"error": "Missing 'task_id' field"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scheduler"))
            from task_scheduler import get_scheduler
            scheduler = get_scheduler()
            removed = scheduler.remove_task(task_id)
            self._send_json({"success": removed, "task_id": task_id})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_scheduler_enable(self):
        """POST /scheduler/enable - Enable/disable a scheduled task."""
        body = self._read_json()
        task_id = body.get("task_id", "")
        enabled = body.get("enabled", True)

        if not task_id:
            self._send_json({"error": "Missing 'task_id' field"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scheduler"))
            from task_scheduler import get_scheduler
            scheduler = get_scheduler()
            updated = scheduler.enable_task(task_id, enabled=enabled)
            self._send_json({"success": updated, "task_id": task_id, "enabled": enabled})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    #  Sandbox Handler 

    def _handle_sandbox_execute(self):
        """POST /sandbox/execute - Execute code in Docker sandbox."""
        body = self._read_json()
        code = body.get("code", "")
        language = body.get("language", "python")
        timeout = body.get("timeout", 30)

        if not code:
            self._send_json({"error": "Missing 'code' field"}, 400)
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sandbox"))
            from docker_sandbox import get_sandbox
            sandbox = get_sandbox()
            result = sandbox.execute(code, language=language, timeout=timeout)
            self._send_json({"success": True, **result})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    #  Brain v2.0 Handlers 

    def _get_brain_v2(self):
        """Get or create BrainV2 singleton, injecting existing brain engine."""
        from brain_v2 import get_brain_v2
        return get_brain_v2(brain_engine=_brain_engine)

    def _handle_brain_v2_status(self):
        """GET /brain/v2/status"""
        try:
            brain = self._get_brain_v2()
            self._send_json({"success": True, **brain.get_status()})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_brain_v2_recall(self):
        """POST /brain/v2/recall - Smart 3-layer recall with token budget."""
        t0 = time.time()
        body = self._read_json()
        query = body.get("message", body.get("query", ""))
        max_tokens = body.get("max_tokens", 1000)

        if not query:
            self._send_json({"error": "Missing 'message' or 'query' field"}, 400)
            return

        try:
            brain = self._get_brain_v2()
            result = brain.recall(query, max_tokens=max_tokens)
            result["success"] = True
            result["duration_ms"] = round((time.time() - t0) * 1000)
            self._send_json(result)
        except Exception as e:
            self._send_json({"success": False, "error": str(e),
                             "duration_ms": round((time.time() - t0) * 1000)})

    def _handle_brain_v2_profile_get(self):
        """GET /brain/v2/profile?key=... or GET /brain/v2/profile (all)."""
        try:
            brain = self._get_brain_v2()
            # Parse query string
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            category = params.get("category", [None])[0]

            if key:
                entry = brain.get_profile(key)
                self._send_json({"success": True, "entry": entry})
            else:
                entries = brain.profile.get_all(category)
                self._send_json({"success": True, "entries": entries,
                                 "count": len(entries)})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_brain_v2_profile_update(self):
        """POST /brain/v2/profile - Update profile entry."""
        body = self._read_json()
        key = body.get("key", "")
        value = body.get("value", "")

        if not key or not value:
            self._send_json({"error": "Missing 'key' or 'value'"}, 400)
            return

        try:
            brain = self._get_brain_v2()
            brain.update_profile(
                key, value,
                category=body.get("category", "fact"),
                importance=body.get("importance", 5)
            )
            self._send_json({"success": True, "key": key})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_brain_v2_task_start(self):
        """POST /brain/v2/task/start - Start working memory task."""
        body = self._read_json()
        description = body.get("description", "")

        if not description:
            self._send_json({"error": "Missing 'description'"}, 400)
            return

        try:
            brain = self._get_brain_v2()
            task_id = brain.start_task(
                description,
                project=body.get("project", ""),
                context=body.get("context"),
                completion_criteria=body.get("completion_criteria"),
            )
            self._send_json({"success": True, "task_id": task_id})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_brain_v2_task_update(self):
        """POST /brain/v2/task/update - Update active task."""
        body = self._read_json()
        task_id = body.get("task_id", "")

        if not task_id:
            self._send_json({"error": "Missing 'task_id'"}, 400)
            return

        try:
            brain = self._get_brain_v2()
            kwargs = {}
            for field in ["description", "status", "context", "open_questions",
                          "completion_criteria", "project"]:
                if field in body:
                    kwargs[field] = body[field]
            updated = brain.update_task(task_id, **kwargs)
            self._send_json({"success": updated, "task_id": task_id})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_brain_v2_task_complete(self):
        """POST /brain/v2/task/complete - Complete a task."""
        body = self._read_json()
        task_id = body.get("task_id", "")

        if not task_id:
            self._send_json({"error": "Missing 'task_id'"}, 400)
            return

        try:
            brain = self._get_brain_v2()
            completed = brain.complete_task(task_id)
            self._send_json({"success": completed, "task_id": task_id})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_brain_v2_tasks(self):
        """GET /brain/v2/tasks - List active tasks."""
        try:
            brain = self._get_brain_v2()
            active = brain.working.get_active_tasks()
            all_tasks = brain.working.get_all_tasks(limit=20)
            self._send_json({
                "success": True,
                "active": active,
                "active_count": len(active),
                "recent": all_tasks,
            })
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_shutdown(self):
        self._send_json({"status": "shutting_down"})
        _shutdown_event.set()


def main():
    global _start_time

    print(f"[BRAIN-SERVER] Starting on {HOST}:{PORT}...")
    print(f"[BRAIN-SERVER] Pre-loading embedding model...")

    t0 = time.time()
    _get_brain_engine()  # Force model load
    load_time = time.time() - t0
    print(f"[BRAIN-SERVER] Model loaded in {load_time:.1f}s")

    _start_time = time.time()

    server = HTTPServer((HOST, PORT), BrainRequestHandler)
    server.timeout = 1.0  # Check shutdown event every second

    # Graceful shutdown on SIGINT/SIGTERM
    def _signal_handler(sig, frame):
        print("\n[BRAIN-SERVER] Signal received, shutting down...")
        _shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"[BRAIN-SERVER] Ready! Listening on http://{HOST}:{PORT}")
    print(f"[BRAIN-SERVER] Endpoints: /recall /capture /context /prefilter /status /health")
    print(f"[BRAIN-SERVER] Skills: /skills /skills/execute /skills/reload")
    print(f"[BRAIN-SERVER] Scheduler: /scheduler/tasks /scheduler/add /scheduler/remove /scheduler/enable")
    print(f"[BRAIN-SERVER] Sandbox: /sandbox/execute")
    print(f"[BRAIN-SERVER] Permission: /permission/check /permission/respond")
    print(f"[BRAIN-SERVER] Brain v2: /brain/v2/status /brain/v2/recall /brain/v2/profile /brain/v2/tasks")
    print(f"[BRAIN-SERVER] Brain v2: /brain/v2/task/start /brain/v2/task/update /brain/v2/task/complete")
    print(f"[BRAIN-SERVER] Control: /shutdown")

    while not _shutdown_event.is_set():
        server.handle_request()

    print("[BRAIN-SERVER] Shutdown complete.")
    server.server_close()


if __name__ == "__main__":
    main()
