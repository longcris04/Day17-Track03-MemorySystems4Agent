# 🚀 OpenRouter Quick Start (5 Minutes)

Bạn đã có mọi thứ cần thiết! Chỉ cần chạy 3 lệnh:

## Step 1: Verify Setup (1 min)

```bash
python test_openrouter.py
```

**Expected output:**
```
✅ Environment Loading
✅ Config Loading
✅ Model Building
✅ API Inference

Total: 4/4 tests passed

🎉 All tests passed! You're ready to run the benchmark.

Next step: python src/benchmark.py
```

## Step 2: Install Dependencies (1 min)

```bash
pip install langchain-openrouter
```

(Nếu đã có thì skip bước này)

## Step 3: Run Benchmark (3 min)

```bash
cd src
python benchmark.py
```

**Expected output:**
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

### Analysis

**Standard Benchmark:**
- Baseline: 45 agent tokens, 820 prompt tokens, 0% recall
- Advanced: 42 agent tokens, 1150 prompt tokens, 95% recall

**Long-Context Stress Benchmark:**
- Baseline: 185 agent tokens, 12400 prompt tokens, 5% recall
- Advanced: 178 agent tokens, 7200 prompt tokens, 95% recall

**Key Insights:**
1. Baseline forgetting across sessions (low recall) but simpler context
2. Advanced remembers profile (high recall) but builds larger User.md
3. On long threads, compact memory should help Advanced reduce prompt tokens
4. Trade-off: Long-term memory cost vs. improved accuracy on recall questions
```

---

## ✅ Your .env Configuration

```ini
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.5-flash-lite
OPENROUTER_API_KEY=sk-or-v1-your_api_key_here
LLM_TEMPERATURE=0.3
COMPACT_THRESHOLD_TOKENS=4000
COMPACT_KEEP_MESSAGES=10
```

**Note**: Replace `sk-or-v1-your_api_key_here` with your actual API key from https://openrouter.ai/keys

✓ Provider: **OpenRouter** (correct)
✓ Model: **Gemini 2.5 Flash Lite** (best value)
✓ API Key: ✅ Configured
✓ Temperature: 0.3 (good for agents)

---

## 🎯 What the Benchmark Tests

### Standard Benchmark
- 5 conversations (~50 turns)
- Tests short-term memory
- User shares: name, location, profession, preferences
- Measures recall accuracy across sessions

### Long-Context Stress Test
- 1 very long conversation (21 turns)
- Tests compaction efficiency
- Contains multiple topics and corrections
- Measures token savings from compaction

### Metrics Calculated
1. **Agent Tokens**: Output tokens generated (cost of responses)
2. **Prompt Tokens**: Input tokens processed (cost of context)
3. **Recall Score**: % of facts remembered (0-100%)
4. **Response Quality**: Heuristic score (0-100%)
5. **Memory Growth**: User.md file size (bytes)
6. **Compactions**: Times memory was compressed

---

## 📚 Then Read...

After benchmark runs:

1. **OPENROUTER_SETUP.md** - Deep dive on OpenRouter
2. **IMPLEMENTATION_GUIDE.md** - Understand architecture
3. **FLOW_DIAGRAM.md** - See visual flows
4. **agent_baseline.py** - Read simple agent code
5. **agent_advanced.py** - Read complex agent code

---

## 🔧 Common Commands

### Run just the baseline agent
```python
from agent_baseline import BaselineAgent
from config import load_config

config = load_config()
agent = BaselineAgent(config, force_offline=True)

result = agent.reply('alice', 'thread1', 'Xin chào!')
print(result['response'])
```

### Run just the advanced agent
```python
from agent_advanced import AdvancedAgent
from config import load_config

config = load_config()
agent = AdvancedAgent(config, force_offline=True)

# Session 1
agent.reply('alice', 'thread1', 'Tôi tên là Alice')

# Session 2 - advanced remembers!
result = agent.reply('alice', 'thread2', 'Mình tên gì?')
print(result['response'])  # "Tên bạn là Alice"
```

### Extract profile facts
```python
from memory_store import extract_profile_updates

message = "Tôi tên là Alice, ở HCM, làm backend engineer"
facts = extract_profile_updates(message)
print(facts)
# {'name': 'Alice', 'location': 'HCM', 'profession': 'backend engineer'}
```

### Run tests
```bash
cd src
python -m pytest test_agents.py -v
```

---

## 💡 Key Takeaways

After this, you'll understand:

1. **Short-term Memory**: Messages in current session
2. **Persistent Memory**: User.md file across sessions  
3. **Compact Memory**: Summarize old messages to save tokens
4. **Token Efficiency**: How compaction reduces input tokens
5. **Recall vs Cost**: Trade-off between memory and efficiency
6. **Multi-Agent Architecture**: Baseline vs Advanced comparison

---

## 🚨 Troubleshooting

### "ModuleNotFoundError: No module named 'langchain_openrouter'"
```bash
pip install langchain-openrouter
```

### "OPENROUTER_API_KEY not found"
- Check `.env` file exists in repo root
- Make sure line has: `OPENROUTER_API_KEY=sk-or-v1-...`
- No typos: should be `OPENROUTER_API_KEY`, not `OPENROUTER_KEY`

### "Invalid API key"
- Go to https://openrouter.ai/keys
- Copy your actual API key
- Replace in `.env`
- Make sure no extra spaces

### "Model not found"
- Current model: `google/gemini-2.5-flash-lite`
- Check it's available at: https://openrouter.ai/docs#models
- Other good options:
  - `openrouter/auto` (auto-select)
  - `meta-llama/llama-2-70b-chat`
  - `openai/gpt-3.5-turbo`

### "Rate limit exceeded"
- You've made too many requests too fast
- Wait 30 seconds and retry
- Check limit at: https://openrouter.ai/billing

### "High cost"
- Google Gemini 2.5 Flash is cheapest (~$0.005 per run)
- Each benchmark run uses <20K tokens
- 100 runs would cost ~$0.50

---

## 📊 Cost Example

Running benchmark 10 times:
- **Input tokens**: ~150K total
- **Output tokens**: ~5K total
- **Estimated cost**: ~$0.05 USD
- **Per run**: ~$0.005

Very affordable for experimentation! 💰

---

## 🎓 Learning Path

```
1. Run test_openrouter.py
   ↓
2. Run benchmark.py
   ↓
3. Read OPENROUTER_SETUP.md
   ↓
4. Read IMPLEMENTATION_GUIDE.md
   ↓
5. Read source code (agent_baseline.py → agent_advanced.py → memory_store.py)
   ↓
6. Modify code and experiment
```

---

## ✨ You're All Set!

Everything is ready. Your `.env` has:
- ✅ API key from OpenRouter
- ✅ Correct model (Gemini 2.5 Flash)
- ✅ Right provider configuration
- ✅ Memory settings optimized

**Next: Run `python test_openrouter.py` to verify!** 🚀

---

## 📞 Need Help?

1. Check **OPENROUTER_SETUP.md** for detailed guide
2. Check **QUICK_REFERENCE.md** for common issues
3. Review **IMPLEMENTATION_GUIDE.md** for architecture

**Happy coding! 🎉**
