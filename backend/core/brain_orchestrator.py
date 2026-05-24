#!/usr/bin/env python3
"""
Brain Orchestrator — The Master Orchestrator

Connects ALL modules into a unified system.
Single API: brain.process_message(msg) -> uses all pillars.

Modules integrated:
- Säule 1: brain_engine (Semantic Memory)
- Säule 2: auto_capture + auto_recall (Auto-Learn)
- Säule 3: knowledge_graph (Knowledge Graph)
- Säule 4: session_manager (Session Intelligence)
- Säule 5: behavior_engine (Proactive Thinking)
- Säule 6: confidence_tracker (Self-Calibration)
- Säule 7: boris_model (Boris Understanding)
- Säule 9+10: reflection (Self-Reflection & Planning)
- Säule 11: poka_yoke (Error Prevention)
- Säule 12: context_engine (Context Engineering)
- Säule 13: lats (Decision Framework)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SRC_DIR = Path(__file__).parent
DATA_DIR = SRC_DIR.parent / "data"


class BrainOrchestrator:
    """Master orchestrator connecting all Javix Brain modules."""

    def __init__(self, lazy: bool = True):
        """
        Initialize orchestrator.
        lazy=True: modules loaded on first use (fast startup).
        lazy=False: all modules loaded immediately.
        """
        self._modules = {}
        self._lazy = lazy
        self._init_time = datetime.now().isoformat()

        if not lazy:
            self._load_all()

    #  Lazy Module Loading 

    def _get(self, name: str):
        if name not in self._modules:
            self._modules[name] = self._load_module(name)
        return self._modules[name]

    def _load_module(self, name: str):
        try:
            if name == "brain_engine":
                from brain_engine import BrainEngine
                return BrainEngine()
            elif name == "knowledge_graph":
                from knowledge_graph import KnowledgeGraph
                return KnowledgeGraph()
            elif name == "session_manager":
                from session_manager import SessionManager
                return SessionManager()
            elif name == "behavior_engine":
                from behavior_engine import BehaviorEngine
                return BehaviorEngine()
            elif name == "boris_model":
                from boris_model import BorisModel
                return BorisModel()
            elif name == "confidence_tracker":
                from confidence_tracker import ConfidenceTracker
                return ConfidenceTracker()
            elif name == "reflection":
                from reflection import ReflectionEngine
                return ReflectionEngine()
            elif name == "poka_yoke":
                from poka_yoke import PokaYoke
                return PokaYoke()
            elif name == "context_engine":
                from context_engine import ContextEngine
                ce = ContextEngine()
                # Register available modules
                for mod_name in ["brain_engine", "knowledge_graph", "session_manager",
                                 "confidence_tracker", "boris_model", "behavior_engine"]:
                    mod = self._modules.get(mod_name)
                    if mod:
                        register_fn = getattr(ce, f"register_{mod_name}", None)
                        if register_fn:
                            register_fn(mod)
                return ce
            elif name == "lats":
                from lats import LATS
                return LATS()
            elif name == "auto_capture":
                from auto_capture import AutoCapture
                return AutoCapture()
            elif name == "auto_recall":
                from auto_recall import AutoRecall
                return AutoRecall()
        except ImportError as e:
            print(f"Warning: Could not load {name}: {e}", file=sys.stderr)
            return None
        return None

    def _load_all(self):
        for name in ["brain_engine", "knowledge_graph", "session_manager",
                      "behavior_engine", "boris_model", "confidence_tracker",
                      "reflection", "poka_yoke", "lats", "auto_capture",
                      "auto_recall", "context_engine"]:
            self._get(name)

    #  Main API 

    def process_message(self, message: str, sender: str = "boris") -> Dict:
        """
        Process an incoming message using all pillars.
        Returns context + metadata for response generation.
        """
        result = {
            "message": message,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "context": "",
            "task_type": "unknown",
            "confidence_note": "",
            "behavior_triggers": [],
            "reflection": None,
        }

        # 1. Task classification (Context Engine)
        ce = self._get("context_engine")
        if ce:
            result["task_type"] = ce.primary_task(message)

        # 2. Behavior logging + triggers
        be = self._get("behavior_engine")
        if be:
            try:
                be.log_interaction(message, sender=sender)
                triggers = be.check_triggers(message)
                result["behavior_triggers"] = triggers if triggers else []
            except Exception:
                pass

        # 3. Boris model update (if from Boris)
        if sender == "boris":
            bm = self._get("boris_model")
            if bm:
                try:
                    bm.update_from_message(message)
                except Exception:
                    pass

            # 3b. Check for corrections (Confidence)
            ch = self._get("confidence_tracker")
            if ch:
                try:
                    from confidence_hooks import detect_correction
                    correction = detect_correction(message)
                    if correction:
                        ch.log_correction(
                            domain=correction.get("domain", "general"),
                            details=message[:200],
                            severity=correction.get("severity", 0.7)
                        )
                except Exception:
                    pass

        # 4. Get context (Context Engine orchestrates all sources)
        if ce:
            try:
                # Register modules that are loaded
                for mod_name in ["brain_engine", "knowledge_graph", "session_manager",
                                 "confidence_tracker", "boris_model", "behavior_engine"]:
                    mod = self._modules.get(mod_name)
                    if mod:
                        register_fn = getattr(ce, f"register_{mod_name}", None)
                        if register_fn:
                            register_fn(mod)
                result["context"] = ce.get_context(message)
            except Exception:
                pass

        # 5. Confidence note
        ct = self._get("confidence_tracker")
        if ct:
            try:
                task_domain = result["task_type"]
                if ct.should_hedge(task_domain):
                    result["confidence_note"] = ct.get_hedge_message(task_domain)
            except Exception:
                pass

        # 6. Pre-reflection (for complex tasks)
        if result["task_type"] in ("coding", "planning", "admin"):
            ref = self._get("reflection")
            if ref:
                try:
                    pre = ref.pre_reflect(message)
                    result["reflection"] = pre.to_prompt()
                except Exception:
                    pass

        return result

    def get_context(self, message: str, max_tokens: int = 4000) -> str:
        """Get assembled context for a message."""
        ce = self._get("context_engine")
        if ce:
            # Ensure modules registered
            for mod_name in ["brain_engine", "knowledge_graph", "session_manager",
                             "confidence_tracker", "boris_model", "behavior_engine"]:
                mod = self._modules.get(mod_name)
                if mod:
                    register_fn = getattr(ce, f"register_{mod_name}", None)
                    if register_fn:
                        register_fn(mod)
            return ce.get_context(message, max_tokens)
        return ""

    def post_conversation(self, messages: List[Dict]) -> Dict:
        """
        Post-conversation processing: auto-capture, session checkpoint, behavior log.
        messages = [{"role": "user"/"assistant", "content": "..."}]
        """
        result = {"captured": 0, "checkpoint": False, "lessons": []}

        # Auto-capture
        ac = self._get("auto_capture")
        be_engine = self._get("brain_engine")
        if ac and be_engine:
            try:
                for msg in messages:
                    if msg.get("role") == "user":
                        captured = ac.capture(msg["content"])
                        for item in captured:
                            be_engine.store(
                                content=item.get("content", ""),
                                category=item.get("category", "fact"),
                                importance=item.get("importance", 5) / 10.0,
                                metadata={"source": "auto_capture"}
                            )
                            result["captured"] += 1
            except Exception:
                pass

        # Session checkpoint
        sm = self._get("session_manager")
        if sm:
            try:
                texts = [m["content"] for m in messages if m.get("content")]
                sm.checkpoint(texts)
                result["checkpoint"] = True
            except Exception:
                pass

        # Post-review (Reflection)
        ref = self._get("reflection")
        if ref:
            try:
                # Simple heuristic: if conversation had corrections -> partial, else success
                has_corrections = any(
                    any(w in m.get("content", "").lower() for w in ["falsch", "nein", "wrong", "actually"])
                    for m in messages if m.get("role") == "user"
                )
                outcome = "partial" if has_corrections else "success"
                topic = messages[0]["content"][:100] if messages else "unknown"
                review = ref.post_review(
                    task=topic, outcome=outcome,
                    lessons=[f"Conversation {'had corrections' if has_corrections else 'completed successfully'}"]
                )
                result["lessons"] = review.lessons
            except Exception:
                pass

        return result

    def get_status(self) -> Dict:
        """Get status of all modules."""
        status = {
            "orchestrator": {
                "init_time": self._init_time,
                "loaded_modules": list(self._modules.keys()),
                "total_modules": 12,
            },
            "modules": {}
        }

        for name in ["brain_engine", "knowledge_graph", "session_manager",
                      "behavior_engine", "boris_model", "confidence_tracker",
                      "reflection", "poka_yoke", "context_engine", "lats",
                      "auto_capture", "auto_recall"]:
            mod = self._modules.get(name)
            if mod is None:
                status["modules"][name] = {"status": "not_loaded"}
            else:
                try:
                    if hasattr(mod, "stats"):
                        status["modules"][name] = {"status": "ok", "stats": mod.stats()}
                    else:
                        status["modules"][name] = {"status": "ok"}
                except Exception as e:
                    status["modules"][name] = {"status": "error", "error": str(e)}

        return status

    def close(self):
        for mod in self._modules.values():
            if mod and hasattr(mod, "close"):
                try:
                    mod.close()
                except Exception:
                    pass


#  CLI 

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Brain Orchestrator CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Show status of all modules")

    p_process = sub.add_parser("process", help="Process a message")
    p_process.add_argument("message", help="Message to process")
    p_process.add_argument("--sender", default="boris")

    p_ctx = sub.add_parser("context", help="Get context for a message")
    p_ctx.add_argument("message", help="Message")
    p_ctx.add_argument("--tokens", type=int, default=4000)

    args = parser.parse_args()

    # Add src to path for imports
    sys.path.insert(0, str(SRC_DIR))

    brain = BrainOrchestrator(lazy=True)
    try:
        if args.cmd == "status":
            brain._load_all()
            print(json.dumps(brain.get_status(), indent=2, default=str))
        elif args.cmd == "process":
            result = brain.process_message(args.message, sender=args.sender)
            print(json.dumps(result, indent=2, default=str))
        elif args.cmd == "context":
            ctx = brain.get_context(args.message, args.tokens)
            print(ctx if ctx else "(no context)")
        else:
            parser.print_help()
    finally:
        brain.close()


if __name__ == "__main__":
    main()
