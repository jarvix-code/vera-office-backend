"""
VERA LLM Worker - Test Suite
Tests all endpoints: /health, /models, /chat

Usage:
    py -3.11 test_worker.py
    
Prerequisites:
    - LLM Worker must be running (port 18793)
    - Run: start_llm_worker.ps1
"""
import requests
import sys
from colorama import init, Fore, Style

init(autoreset=True)

LLM_WORKER_URL = "http://127.0.0.1:18793"


def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")


def print_success(text):
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")


def print_error(text):
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")


def print_info(text):
    print(f"{Fore.YELLOW}ℹ️  {text}{Style.RESET_ALL}")


def test_health():
    """Test /health endpoint"""
    print_header("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{LLM_WORKER_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   Model: {data['model']}")
            print(f"   Port: {data['port']}")
            print(f"   Model Loaded: {data['model_loaded']}")
            print(f"   Context Window: {data['context_window']}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to LLM Worker (port 18793)")
        print_info("Start the worker first: .\\start_llm_worker.ps1")
        return False
    
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


def test_models():
    """Test /models endpoint"""
    print_header("TEST 2: List Models")
    
    try:
        response = requests.get(f"{LLM_WORKER_URL}/models", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Models list retrieved")
            
            for model in data['models']:
                print(f"   Model ID: {model['id']}")
                print(f"   Type: {model['type']}")
                print(f"   Context Window: {model['context_window']}")
                print(f"   Path: {model['path']}")
            
            return True
        else:
            print_error(f"Models list failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Models error: {e}")
        return False


def test_chat_simple():
    """Test /chat with simple question"""
    print_header("TEST 3: Simple Chat")
    
    try:
        question = "Was ist Hygiene-Management in einer Zahnarztpraxis?"
        print_info(f"Frage: {question}")
        
        response = requests.post(
            f"{LLM_WORKER_URL}/chat",
            json={
                "message": question,
                "max_tokens": 256,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Chat response generated")
            print(f"   Tokens Used: {data['tokens_used']}")
            print(f"   Processing Time: {data['processing_time_ms']}ms")
            print(f"\n   Response:\n   {Fore.WHITE}{data['response'][:200]}...{Style.RESET_ALL}")
            return True
        else:
            print_error(f"Chat failed: {response.status_code}")
            print(response.text)
            return False
    
    except requests.exceptions.Timeout:
        print_error("Chat timeout (30s)")
        return False
    
    except Exception as e:
        print_error(f"Chat error: {e}")
        return False


def test_chat_with_context():
    """Test /chat with context"""
    print_header("TEST 4: Chat with Context")
    
    try:
        question = "Wie oft muss das gemacht werden?"
        context = "Hygieneplan: Instrumente müssen nach jeder Behandlung sterilisiert werden. Oberflächen werden täglich desinfiziert."
        
        print_info(f"Frage: {question}")
        print_info(f"Kontext: {context[:80]}...")
        
        response = requests.post(
            f"{LLM_WORKER_URL}/chat",
            json={
                "message": question,
                "context": context,
                "max_tokens": 256,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Context-aware chat response generated")
            print(f"   Tokens Used: {data['tokens_used']}")
            print(f"   Processing Time: {data['processing_time_ms']}ms")
            print(f"\n   Response:\n   {Fore.WHITE}{data['response'][:200]}...{Style.RESET_ALL}")
            return True
        else:
            print_error(f"Chat with context failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Chat with context error: {e}")
        return False


def test_performance():
    """Test response time for multiple requests"""
    print_header("TEST 5: Performance Test")
    
    questions = [
        "Was ist ein QM-Handbuch?",
        "Wie dokumentiere ich eine Behandlung?",
        "Was bedeutet Datenschutz in der Praxis?"
    ]
    
    times = []
    
    for i, question in enumerate(questions, 1):
        try:
            response = requests.post(
                f"{LLM_WORKER_URL}/chat",
                json={
                    "message": question,
                    "max_tokens": 128,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                time_ms = data['processing_time_ms']
                times.append(time_ms)
                print(f"   Request {i}/3: {time_ms}ms")
            else:
                print_error(f"Request {i} failed")
        
        except Exception as e:
            print_error(f"Request {i} error: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        print_success(f"Average response time: {avg_time:.0f}ms")
        
        if avg_time < 2000:
            print_success("Performance: EXCELLENT (< 2s)")
        elif avg_time < 5000:
            print_info("Performance: GOOD (< 5s)")
        else:
            print_error("Performance: SLOW (> 5s)")
        
        return True
    else:
        print_error("Performance test failed")
        return False


def main():
    """Run all tests"""
    print(f"{Fore.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          VERA LLM Worker - Test Suite                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)
    
    tests = [
        ("Health Check", test_health),
        ("List Models", test_models),
        ("Simple Chat", test_chat_simple),
        ("Chat with Context", test_chat_with_context),
        ("Performance", test_performance)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            failed += 1
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"   Total: {passed + failed}")
    print(f"   {Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
    print(f"   {Fore.RED}Failed: {failed}{Style.RESET_ALL}")
    
    if failed == 0:
        print(f"\n{Fore.GREEN}{'🎉 ALL TESTS PASSED! 🎉'}{Style.RESET_ALL}")
        sys.exit(0)
    else:
        print(f"\n{Fore.RED}{'❌ SOME TESTS FAILED'}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
