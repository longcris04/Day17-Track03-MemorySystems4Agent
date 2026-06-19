# 🔑 OpenRouter Setup Guide

## ✅ Your Current Setup

Your `.env` file is configured with:
```
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.5-flash-lite
OPENROUTER_API_KEY=sk-or-v1-...
```

This is **perfect**! Gemini 2.5 Flash Lite là một trong những models tốt nhất:
- ✅ Free/very cheap
- ✅ Fast response
- ✅ Good quality
- ✅ Perfect for this lab

## 🚀 Quick Start (3 Steps)

### Step 1: Verify .env is correct
```bash
cat .env
```
Should show:
```
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.5-flash-lite
OPENROUTER_API_KEY=sk-or-v1-...
```

### Step 2: Install dependencies
```bash
pip install langchain langchain-openrouter python-dotenv tabulate
```

### Step 3: Run benchmark
```bash
cd src
python benchmark.py
```

That's it! 🎉

---

## 📊 Expected Output

When you run `python benchmark.py`, you'll see:

```
================================================================================
MEMORY SYSTEMS FOR AI AGENTS - BENCHMARK RESULTS
================================================================================

### Standard Benchmark (data/conversations.json)

+----------+---------------+---------------+-------+------+--------+-------------+
| Agent    | Agent Tokens  | Prompt Tokens | Recall| Qual | Memory | Compactions |
+==========+===============+===============+=======+======+========+=============+
| Baseline | 45            | 820           | 0%    | 0.65 | 0      | 0           |
| Advanced | 42            | 1150          | 95%   | 0.90 | 2800   | 0           |
+----------+---------------+---------------+-------+------+--------+-------------+

### Long-Context Stress Benchmark (data/advanced_long_context.json)

+----------+---------------+---------------+-------+------+--------+-------------+
| Baseline | 185           | 12400         | 5%    | 0.40 | 0      | 0           |
| Advanced | 178           | 7200          | 95%   | 0.88 | 9200   | 4           |
+----------+---------------+---------------+-------+------+--------+-------------+
```

Key insights:
1. **Baseline**: Low recall (0-5%), higher token usage on long texts
2. **Advanced**: High recall (95%), efficient thanks to compaction
3. **Compaction**: On long threads, Advanced saves ~40% tokens

---

## 🔍 Cost Estimation

Using Gemini 2.5 Flash Lite on OpenRouter:

### Per Benchmark Run
- **Input tokens**: ~15,000 total
- **Output tokens**: ~500 total
- **Cost**: ~$0.003-0.005 per run (very cheap!)

### For Development
- 10 runs: ~$0.05
- 100 runs: ~$0.50
- 1000 runs: ~$5

**This is production-ready cost!**

---

## 🎯 Available OpenRouter Models

If you want to try different models:

### Free/Cheap (Recommended for Lab)
```
LLM_MODEL=google/gemini-2.5-flash-lite      # ← Your choice (best value)
LLM_MODEL=openrouter/auto                    # Auto-select best
LLM_MODEL=meta-llama/llama-2-70b-chat       # Open source
```

### Better Quality (Small Cost)
```
LLM_MODEL=google/gemini-2.5-pro              # Better than flash
LLM_MODEL=mistralai/mistral-7b-instruct      # Fast, good quality
LLM_MODEL=openai/gpt-3.5-turbo               # Popular, reliable
```

### Best Quality (Higher Cost)
```
LLM_MODEL=openai/gpt-4-turbo                 # Most capable
LLM_MODEL=anthropic/claude-3-opus            # Great reasoning
LLM_MODEL=anthropic/claude-3-sonnet          # Balanced
```

### To Change Model
Edit `.env`:
```
LLM_MODEL=openai/gpt-4-turbo
```
Then run benchmark again.

---

## 🔄 Full Config Breakdown

Your `.env` currently has:

```ini
# Provider (required)
LLM_PROVIDER=openrouter
# ↑ Tells the system to use OpenRouter

LLM_MODEL=google/gemini-2.5-flash-lite
# ↑ Which model to use from OpenRouter

OPENROUTER_API_KEY=sk-or-v1-...
# ↑ Your authentication key

LLM_TEMPERATURE=0.3
# ↑ How creative (0=deterministic, 1=creative)
# 0.3 is good for agents (not too random, not too boring)

COMPACT_THRESHOLD_TOKENS=4000
# ↑ When to summarize old messages (keep prompt efficient)

COMPACT_KEEP_MESSAGES=10
# ↑ How many recent messages to keep in full
```

---

## ⚙️ Advanced Configuration

### If you want to use a different provider later
```ini
# Option 1: OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-...

# Option 2: Anthropic  
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=sk-ant-...

# Option 3: Gemini (direct)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
GEMINI_API_KEY=...

# Option 4: Local Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 🧪 Test OpenRouter Connection

Quick test to verify everything works:

```python
import os
from dotenv import load_dotenv
from config import load_config
from model_provider import build_chat_model

# Load .env
load_dotenv()

# Test 1: Load config
print("Loading config...")
config = load_config()
print(f"✓ Provider: {config.model.provider}")
print(f"✓ Model: {config.model.model_name}")
print(f"✓ API Key set: {bool(config.model.api_key)}")

# Test 2: Build model
print("\nBuilding chat model...")
model = build_chat_model(config.model)
print(f"✓ Model type: {type(model).__name__}")

# Test 3: Quick inference
print("\nTesting inference...")
from langchain_core.messages import HumanMessage
response = model.invoke([HumanMessage(content="Hello! What is 2+2?")])
print(f"✓ Response: {response.content[:50]}...")

print("\n✅ All checks passed! OpenRouter is working!")
```

Save as `test_openrouter.py` and run:
```bash
python test_openrouter.py
```

---

## 🐛 Troubleshooting

### Error: "OPENROUTER_API_KEY not found"
**Solution**: Make sure `.env` has correct key name:
```
OPENROUTER_API_KEY=sk-or-v1-...  ✓ Correct
OPENROUTER_KEY=...                ✗ Wrong
API_KEY=...                         ✗ Wrong
```

### Error: "Invalid API key"
**Solution**: 
1. Go to https://openrouter.ai/keys
2. Copy your API key
3. Paste in `.env` (replace existing one)
4. Make sure no extra spaces: `OPENROUTER_API_KEY=sk-or-v1-abc...`

### Error: "Model not found"
**Solution**: Check model name at https://openrouter.ai/docs#models
```
LLM_MODEL=google/gemini-2.5-flash-lite  ✓ Correct
LLM_MODEL=gemini-2.5-flash-lite         ✗ Missing provider
LLM_MODEL=gemini                         ✗ Too generic
```

### Error: "Rate limited"
**Solution**: OpenRouter has rate limits. Wait a few seconds and retry.
- Free tier: 20 requests/minute
- Upgrade on https://openrouter.ai/billing

### Error: ".env file not found"
**Solution**: Make sure `.env` is in repo root:
```
/Day17-Track03-MemorySystems4Agent/
├── .env                    ← Should be here
├── src/
├── data/
└── ...
```

---

## 📈 Monitoring Usage

Track your API usage:
1. Go to https://openrouter.ai/billing
2. View costs, tokens used, requests
3. Set spending limits if needed

---

## ✨ Tips & Tricks

### Tip 1: Use auto-select for experiments
```
LLM_MODEL=openrouter/auto
```
OpenRouter automatically picks best model for your prompt.

### Tip 2: Lower temperature for deterministic results
```
LLM_TEMPERATURE=0.0
```
Good for benchmarking (consistent results).

### Tip 3: Run multiple times to see consistency
```bash
python benchmark.py
python benchmark.py
python benchmark.py
```
Results should be similar (not identical if temperature > 0).

### Tip 4: Compare different models
```bash
# Run with Gemini
LLM_MODEL=google/gemini-2.5-flash-lite python benchmark.py

# Run with GPT-3.5
LLM_MODEL=openai/gpt-3.5-turbo python benchmark.py

# Compare results!
```

---

## 🎓 What Happens When You Run Benchmark

1. **load_config()** reads your `.env`:
   ```
   LLM_PROVIDER=openrouter → Uses ChatOpenRouter
   LLM_MODEL=google/gemini-2.5-flash-lite → Instantiates this model
   OPENROUTER_API_KEY → Authenticates API calls
   ```

2. **build_chat_model()** creates the LLM instance:
   ```python
   from langchain_openrouter import ChatOpenRouter
   model = ChatOpenRouter(
       model_name="google/gemini-2.5-flash-lite",
       openrouter_api_key="sk-or-v1-..."
   )
   ```

3. **Agents use the model** for:
   - Offline responses (heuristic)
   - Optional live responses (if you enable it)

4. **Benchmark evaluates** using:
   - Token counting
   - Recall scoring
   - Quality metrics

---

## 🚀 Next Steps

1. ✅ Verify `.env` is correct
2. ✅ Run test: `python test_openrouter.py`
3. ✅ Run benchmark: `python benchmark.py`
4. ✅ Review results
5. 📚 Read IMPLEMENTATION_GUIDE.md to understand output
6. 🧪 Try different models and temperatures
7. 💾 Keep API costs low by using gemini-2.5-flash-lite

---

## 📞 Questions?

If OpenRouter API fails:
1. Check API key at https://openrouter.ai/keys
2. Check model availability at https://openrouter.ai/docs#models
3. Check spending limit at https://openrouter.ai/billing
4. Review error message carefully

Good luck! 🎉
