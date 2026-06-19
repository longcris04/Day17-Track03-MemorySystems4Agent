#!/usr/bin/env python3
"""Quick test to verify OpenRouter API setup works."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_env_loading():
    """Test 1: Check .env is being loaded correctly."""
    print("=" * 60)
    print("TEST 1: Loading .env file")
    print("=" * 60)

    import os
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env"
    print(f"Looking for .env at: {env_path}")
    print(f"File exists: {env_path.exists()}")

    if not env_path.exists():
        print("❌ .env file not found!")
        return False

    load_dotenv(env_path)

    provider = os.getenv("LLM_PROVIDER")
    model = os.getenv("LLM_MODEL")
    api_key = os.getenv("OPENROUTER_API_KEY")

    print(f"\n✓ LLM_PROVIDER: {provider}")
    print(f"✓ LLM_MODEL: {model}")
    print(f"✓ OPENROUTER_API_KEY: {api_key[:20]}..." if api_key else "✗ OPENROUTER_API_KEY: Not set")

    if provider != "openrouter":
        print(f"\n❌ Provider should be 'openrouter', got '{provider}'")
        return False

    if not api_key or not api_key.startswith("sk-or-v1-"):
        print(f"\n❌ Invalid API key format")
        return False

    print("\n✅ .env file loaded correctly!\n")
    return True


def test_config_loading():
    """Test 2: Check config.py reads environment variables correctly."""
    print("=" * 60)
    print("TEST 2: Loading configuration")
    print("=" * 60)

    from config import load_config

    try:
        config = load_config()
        print(f"✓ Config loaded successfully")
        print(f"✓ Provider: {config.model.provider}")
        print(f"✓ Model: {config.model.model_name}")
        print(f"✓ Base dir: {config.base_dir}")
        print(f"✓ State dir: {config.state_dir}")
        print(f"✓ Data dir: {config.data_dir}")
        print(f"✓ API key set: {bool(config.model.api_key)}")
        print(f"✓ Temperature: {config.model.temperature}")

        if config.model.provider != "openrouter":
            print(f"\n❌ Provider mismatch: expected 'openrouter', got '{config.model.provider}'")
            return False

        if not config.model.api_key:
            print(f"\n❌ API key not loaded from config")
            return False

        print("\n✅ Configuration loaded correctly!\n")
        return True

    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False


def test_model_building():
    """Test 3: Check if we can instantiate the ChatOpenRouter model."""
    print("=" * 60)
    print("TEST 3: Building ChatOpenRouter model")
    print("=" * 60)

    from config import load_config
    from model_provider import build_chat_model

    try:
        config = load_config()
        print(f"Building model with provider='{config.model.provider}'...")

        model = build_chat_model(config.model)

        print(f"✓ Model type: {type(model).__name__}")
        print(f"✓ Model instantiated successfully")
        print(f"✓ Model ready for inference")

        print("\n✅ Model built successfully!\n")
        return True

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print(f"\nTry installing: pip install langchain-openrouter")
        return False
    except Exception as e:
        print(f"❌ Error building model: {e}")
        return False


def test_inference():
    """Test 4: Make a quick API call to verify authentication."""
    print("=" * 60)
    print("TEST 4: Testing inference (quick API call)")
    print("=" * 60)

    from config import load_config
    from model_provider import build_chat_model
    from langchain_core.messages import HumanMessage

    try:
        config = load_config()
        model = build_chat_model(config.model)

        print(f"Making test request to OpenRouter...")
        print(f"Model: {config.model.model_name}")
        print(f"Temperature: {config.model.temperature}")

        # Simple test message
        message = HumanMessage(content="What is 2+2? Answer in one word.")

        print(f"\nSending message: '{message.content}'")
        print(f"Waiting for response...")

        response = model.invoke([message])

        print(f"\n✓ Response received!")
        print(f"✓ Content: {response.content}")

        print("\n✅ API call successful!\n")
        return True

    except Exception as e:
        print(f"❌ Error during inference: {e}")
        print(f"\nCommon issues:")
        print(f"  - Invalid API key (check https://openrouter.ai/keys)")
        print(f"  - Rate limit exceeded (wait a moment and retry)")
        print(f"  - Model not available (check https://openrouter.ai/docs#models)")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  OpenRouter Setup Verification Tests".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    # Test 1
    results.append(("Environment Loading", test_env_loading()))

    # Test 2
    results.append(("Config Loading", test_config_loading()))

    # Test 3
    results.append(("Model Building", test_model_building()))

    # Test 4 (optional, might fail if API issues)
    results.append(("API Inference", test_inference()))

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! You're ready to run the benchmark.")
        print("\nNext step: python src/benchmark.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
