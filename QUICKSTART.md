# 🚀 Quick Start Guide

## 1️⃣ Setup Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install langchain langgraph langchain-openai langchain-google-genai \
    langchain-anthropic langchain-ollama langchain-openrouter python-dotenv \
    tabulate pytest
```

## 2️⃣ Set API Keys (Choose One)

Create a `.env` file in the repo root:

### Option A: OpenAI
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-...
```

### Option B: Anthropic
```
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=sk-ant-...
```

### Option C: Gemini
```
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
GEMINI_API_KEY=...
```

### Option D: Ollama (Local, Free!)
```
LLM_PROVIDER=ollama
LLM_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434

# First install Ollama:
# https://ollama.ai/
# Then: ollama pull llama2
```

## 3️⃣ Quick Test

Run a simple agent test:

```bash
cd src
python -c "
from agent_advanced import AdvancedAgent
from config import load_config

# Load config (will use .env or defaults)
config = load_config()

# Create agent (offline mode = no API calls needed)
agent = AdvancedAgent(config, force_offline=True)

# Test it
result = agent.reply('alice', 'thread1', 'Tôi tên là Alice')
print('Response:', result['response'])
print('Tokens:', result['token_usage'])

# Test recall (should remember)
result2 = agent.reply('alice', 'thread2', 'Mình tên gì?')
print('Recall response:', result2['response'])
"
```

## 4️⃣ Run Full Benchmark

```bash
cd src
python benchmark.py
```

This will:
- Load 2 datasets (standard + long-context)
- Run Baseline agent on each
- Run Advanced agent on each
- Print comparison tables
- Show key insights

Expected output:
```
================================================================================
MEMORY SYSTEMS FOR AI AGENTS - BENCHMARK RESULTS
================================================================================

### Standard Benchmark (data/conversations.json)

+----------+---------------+---------------+-------+------+--------+-------------+
| Agent    | Agent Tokens  | Prompt Tokens | Recall| Qual | Memory | Compactions |
+==========+===============+===============+=======+======+========+=============+
| Baseline | 500           | 800           | 0%    | 0.65 | 0      | 0           |
| Advanced | 480           | 1200          | 95%   | 0.90 | 2500   | 0           |
+----------+---------------+---------------+-------+------+--------+-------------+

### Long-Context Stress Benchmark (data/advanced_long_context.json)

+----------+---------------+---------------+-------+------+--------+-------------+
| Baseline | 2100          | 15000         | 5%    | 0.40 | 0      | 0           |
| Advanced | 2050          | 8000          | 95%   | 0.88 | 8000   | 4           |
+----------+---------------+---------------+-------+------+--------+-------------+

### Analysis

**Standard Benchmark:**
- Baseline: 500 agent tokens, 800 prompt tokens, 0% recall
- Advanced: 480 agent tokens, 1200 prompt tokens, 95% recall

**Long-Context Stress Benchmark:**
- Baseline: 2100 agent tokens, 15000 prompt tokens, 5% recall
- Advanced: 2050 agent tokens, 8000 prompt tokens, 95% recall

**Key Insights:**
1. Baseline forgetting across sessions (low recall) but simpler context
2. Advanced remembers profile (high recall) but builds larger User.md
3. On long threads, compact memory should help Advanced reduce prompt tokens
4. Trade-off: Long-term memory cost vs. improved accuracy on recall questions
```

## 5️⃣ Run Unit Tests

```bash
cd src
python -m pytest test_agents.py -v
```

Tests verify:
- ✅ User.md read/write/edit functionality
- ✅ Compact memory triggers at threshold
- ✅ Advanced remembers across sessions
- ✅ Baseline forgets across sessions

## 6️⃣ Explore Code

Key files to read:
1. `IMPLEMENTATION_GUIDE.md` - Detailed architecture & function explanations
2. `FLOW_DIAGRAM.md` - Visual flow of agent operations
3. `src/agent_baseline.py` - Simple agent (read this first!)
4. `src/agent_advanced.py` - Complex agent with 3 memory layers
5. `src/memory_store.py` - Core memory infrastructure

## 7️⃣ Manual Testing

Play with agents interactively:

```python
from agent_baseline import BaselineAgent
from agent_advanced import AdvancedAgent
from config import load_config

config = load_config()

baseline = BaselineAgent(config, force_offline=True)
advanced = AdvancedAgent(config, force_offline=True)

user_id = 'test_user'

# Session 1: Share info
print("=== SESSION 1 ===")
print("Baseline:", baseline.reply(user_id, 'session1', 'Tôi tên là Alice'))
print("Advanced:", advanced.reply(user_id, 'session1', 'Tôi tên là Alice'))

# Session 2: Test recall (fresh thread)
print("\n=== SESSION 2 ===")
print("Baseline:", baseline.reply(user_id, 'session2', 'Mình tên gì?'))
print("Advanced:", advanced.reply(user_id, 'session2', 'Mình tên gì?'))

# Session 3: Long conversation (test compaction)
print("\n=== SESSION 3: LONG CONVERSATION ===")
for i in range(10):
    msg = f"Message {i}: " + "a" * 100
    baseline.reply(user_id, 'long_session', msg)
    advanced.reply(user_id, 'long_session', msg)

print(f"Baseline tokens: {baseline.prompt_token_usage('long_session')}")
print(f"Advanced tokens: {advanced.prompt_token_usage('long_session')}")
print(f"Advanced compactions: {advanced.compaction_count('long_session')}")
```

## 🎯 What to Understand

After running the code, you should understand:

1. **Short-term Memory (Layer 1)**
   - Both agents keep messages in current thread
   - Baseline discards when thread changes
   - Advanced keeps in CompactMemoryManager

2. **Persistent Memory (Layer 2 - Advanced only)**
   - User.md stores stable facts
   - Extracted from user messages
   - Survives across sessions
   - Enables cross-session recall

3. **Compact Memory (Layer 3 - Advanced only)**
   - Summarizes old messages
   - Keeps recent messages in full
   - Triggered when token threshold exceeded
   - Reduces prompt token growth on long threads

4. **Token Trade-offs**
   - Baseline: Low cost initially, explodes on long threads
   - Advanced: Higher initial cost (User.md), but compaction saves on long threads
   - Recall vs efficiency trade-off

## 📚 Next Steps

1. Read `IMPLEMENTATION_GUIDE.md` for detailed explanations
2. Read `FLOW_DIAGRAM.md` for visual understanding
3. Look at comments in source files
4. Modify threshold values and see impact:
   ```python
   # Lower threshold = more compactions
   COMPACT_THRESHOLD_TOKENS=1000
   COMPACT_KEEP_MESSAGES=5
   ```
5. Try different message types and see what gets extracted to User.md

## ❓ FAQ

**Q: Can I run without API keys?**
A: Yes! Use `force_offline=True` when creating agents. This disables real LLM calls and uses deterministic responses.

**Q: How do I change compaction settings?**
A: Edit `.env`:
```
COMPACT_THRESHOLD_TOKENS=4000  # Trigger compaction when this threshold exceeded
COMPACT_KEEP_MESSAGES=10       # Keep last 10 messages in full after compaction
```

**Q: Which agent should I use in production?**
A: It depends:
- **Baseline**: Simple chatbots, single-turn interactions, API-cost-sensitive
- **Advanced**: User-facing assistants, multi-session apps, long conversations

**Q: How accurate is token estimation?**
A: It's a rough heuristic (`len(text) // 4`). For production, use actual provider tokenizer.

---

Ready? Start with step 1 above! 🎉
