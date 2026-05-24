"""
Test LLM Router - Multi-LLM Architecture

Tests:
1. LLM Router Initialization
2. Task Routing (Fast vs Local)
3. Fallback Logic (no API key → Local for all)
4. Logging (which LLM is used)
"""
import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_router_initialization():
    """Test 1: Router initialization."""
    logger.info("=" * 60)
    logger.info("TEST 1: LLM Router Initialization")
    logger.info("=" * 60)
    
    from backend.core.ai.llm_router import llm_router
    
    status = llm_router.get_routing_status()
    
    logger.info(f"Fast LLM Available: {status['fast_llm_available']}")
    logger.info(f"Fast LLM Provider: {status['fast_llm_provider']}")
    logger.info(f"Local LLM Available: {status['local_llm_available']}")
    logger.info(f"Local LLM Provider: {status['local_llm_provider']}")
    logger.info(f"Routing Mode: {status['routing_mode']}")
    
    assert status['routing_mode'] in ['hybrid', 'local_only', 'none'], "Invalid routing mode"
    
    logger.info("✅ TEST 1 PASSED")
    return status


def test_chat_routing(status):
    """Test 2: Chat task routing (should use Fast LLM if available)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Chat Task Routing")
    logger.info("=" * 60)
    
    from backend.core.ai.llm_router import llm_router
    
    chat_llm = llm_router.get_llm("chat")
    
    if chat_llm:
        logger.info(f"Chat routed to: {chat_llm.get_provider_name()}")
        
        # Expected behavior:
        # - If Fast LLM available → Fast LLM
        # - If Fast LLM unavailable → Local LLM
        if status['fast_llm_available']:
            assert status['fast_llm_provider'] in chat_llm.get_provider_name(), \
                "Chat should use Fast LLM when available"
            logger.info("✅ Correctly routed to Fast LLM")
        else:
            assert "Local" in chat_llm.get_provider_name(), \
                "Chat should fallback to Local LLM when Fast unavailable"
            logger.info("✅ Correctly fallback to Local LLM")
    else:
        logger.warning("⚠️ No LLM available for chat")
    
    logger.info("✅ TEST 2 PASSED")


def test_classification_routing(status):
    """Test 3: Classification task routing (should ALWAYS use Local LLM)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Classification Task Routing")
    logger.info("=" * 60)
    
    from backend.core.ai.llm_router import llm_router
    
    classifier_llm = llm_router.get_llm("doc_classification")
    
    if classifier_llm:
        logger.info(f"Classification routed to: {classifier_llm.get_provider_name()}")
        
        # Classification should ALWAYS use Local LLM (offline-first, Background task)
        assert "Local" in classifier_llm.get_provider_name(), \
            "Classification should ALWAYS use Local LLM"
        logger.info("✅ Correctly routed to Local LLM (offline-first)")
    else:
        logger.warning("⚠️ No LLM available for classification")
    
    logger.info("✅ TEST 3 PASSED")


def test_agent_integration():
    """Test 4: Agent integration (uses Router for chat)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Agent Integration")
    logger.info("=" * 60)
    
    from backend.core.ai.agent import agent
    
    # Simulate a chat message
    response = agent.chat("Hallo VERA!", session_id="test")
    
    logger.info(f"Agent Response: {response.message[:100]}...")
    logger.info(f"Suggestions: {response.suggestions}")
    
    assert response.message, "Agent should return a message"
    assert len(response.message) > 0, "Message should not be empty"
    
    logger.info("✅ TEST 4 PASSED")


def test_classifier_integration():
    """Test 5: Classifier integration (uses Router for classification)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Classifier Integration")
    logger.info("=" * 60)
    
    from backend.core.ai.classifier import classifier
    
    # Simulate OCR text
    ocr_text = """
    Rechnung Nr. 2024-001
    Datum: 08.03.2026
    Gesamtbetrag: 1.234,56 EUR
    MwSt: 234,56 EUR
    """
    
    result = classifier.classify(ocr_text)
    
    logger.info(f"Category: {result['category']}")
    logger.info(f"Confidence: {result['confidence']:.2f}")
    logger.info(f"Reasoning: {result['reasoning']}")
    logger.info(f"Available: {result['available']}")
    
    assert 'category' in result, "Classifier should return a category"
    assert 'confidence' in result, "Classifier should return confidence"
    
    logger.info("✅ TEST 5 PASSED")


def main():
    """Run all tests."""
    logger.info("\n" + "#" * 60)
    logger.info("# VERA Multi-LLM Router Test Suite")
    logger.info("#" * 60 + "\n")
    
    try:
        # Test 1: Router Initialization
        status = test_router_initialization()
        
        # Test 2: Chat Routing
        test_chat_routing(status)
        
        # Test 3: Classification Routing
        test_classification_routing(status)
        
        # Test 4: Agent Integration
        test_agent_integration()
        
        # Test 5: Classifier Integration
        test_classifier_integration()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info(f"\nRouting Mode: {status['routing_mode']}")
        logger.info("Fast LLM: " + ("✅ Available" if status['fast_llm_available'] else "❌ Not Available (no API key)"))
        logger.info("Local LLM: " + ("✅ Available" if status['local_llm_available'] else "❌ Not Available (model not loaded)"))
        
        if status['routing_mode'] == 'hybrid':
            logger.info("\n✅ Hybrid Mode Active:")
            logger.info("   - User-facing tasks (chat) → Fast Cloud LLM")
            logger.info("   - Background tasks (classification) → Local LLM")
        elif status['routing_mode'] == 'local_only':
            logger.info("\n⚠️ Local-Only Mode Active:")
            logger.info("   - Fast LLM not configured (no API key)")
            logger.info("   - All tasks → Local LLM")
            logger.info("   - To enable Fast LLM: Set OPENAI_API_KEY in .env")
        else:
            logger.info("\n❌ No LLM Available:")
            logger.info("   - Local LLM model not found")
            logger.info("   - Fast LLM API key not set")
            logger.info("   - VERA will use template-based responses only")
        
        return 0
    
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
