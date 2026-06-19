# 🎯 Quick Reference Card

## Class Hierarchy

```
ProviderConfig
  ├─ provider: str (openai, anthropic, gemini, ollama, custom, openrouter)
  ├─ model_name: str
  ├─ temperature: float
  ├─ api_key: str | None
  └─ base_url: str | None

LabConfig
  ├─ base_dir, data_dir, state_dir: Path
  ├─ compact_threshold_tokens: int
  ├─ compact_keep_messages: int
  ├─ model: ProviderConfig
  └─ judge_model: ProviderConfig

SessionState (Baseline only)
  ├─ messages: list[dict]
  ├─ token_usage: int
  └─ prompt_tokens_processed: int

BaselineAgent
  ├─ sessions: dict[thread_id → SessionState]
  ├─ reply(user_id, thread_id, message) → dict
  ├─ token_usage(thread_id) → int
  ├─ prompt_token_usage(thread_id) → int
  └─ compaction_count(thread_id) → int (always 0)

UserProfileStore
  ├─ root_dir: Path
  ├─ path_for(user_id) → Path
  ├─ read_text(user_id) → str
  ├─ write_text(user_id, content) → Path
  ├─ edit_text(user_id, search, replace) → bool
  └─ file_size(user_id) → int

CompactMemoryManager
  ├─ threshold_tokens: int
  ├─ keep_messages: int
  ├─ state: dict[thread_id → {messages, summary, compactions}]
  ├─ append(thread_id, role, content) → None
  ├─ context(thread_id) → dict
  └─ compaction_count(thread_id) → int

AdvancedAgent
  ├─ profile_store: UserProfileStore
  ├─ compact_memory: CompactMemoryManager
  ├─ thread_tokens: dict
  ├─ thread_prompt_tokens: dict
  ├─ reply(user_id, thread_id, message) → dict
  ├─ token_usage(thread_id) → int
  ├─ prompt_token_usage(thread_id) → int
  ├─ memory_file_size(user_id) → int
  └─ compaction_count(thread_id) → int

BenchmarkRow
  ├─ agent_name: str
  ├─ agent_tokens_only: int
  ├─ prompt_tokens_processed: int
  ├─ recall_score: float (0-1)
  ├─ response_quality: float (0-1)
  ├─ memory_growth_bytes: int
  └─ compactions: int
```

## Key Functions

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `estimate_tokens(text)` | Heuristic token count | str | int |
| `extract_profile_updates(message)` | Extract profile facts | str | dict |
| `summarize_messages(messages)` | Compact old messages | list | str |
| `normalize_provider(name)` | Fix typos in provider names | str | str |
| `build_chat_model(config)` | Create LLM instance | ProviderConfig | ChatModel |
| `load_config(base_dir)` | Load config from env | Path\|None | LabConfig |
| `recall_points(answer, expected)` | Score recall accuracy | (str, list) | float |
| `heuristic_quality(answer, expected)` | Score response quality | (str, list) | float |
| `run_agent_benchmark(...)` | Benchmark one agent | ... | BenchmarkRow |
| `format_rows(rows)` | Format results table | list | str |

## Environment Variables

```bash
# Provider (required)
LLM_PROVIDER=openai|anthropic|gemini|ollama|custom|openrouter

# Model (required)
LLM_MODEL=gpt-4-turbo|claude-3-sonnet|gemini-pro|llama2

# Temperature (optional, default 0.3)
LLM_TEMPERATURE=0.3

# Provider-specific keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
CUSTOM_BASE_URL=...
CUSTOM_API_KEY=...

# Compact memory settings (optional)
COMPACT_THRESHOLD_TOKENS=4000    # When to compact
COMPACT_KEEP_MESSAGES=10         # How many to keep
```

## Agent Comparison

| Feature | Baseline | Advanced |
|---------|----------|----------|
| **Short-term memory** | ✅ | ✅ |
| **Session handling** | Per-thread, forgets | Per-thread, with compact |
| **Persistent memory (User.md)** | ❌ | ✅ |
| **Profile extraction** | ❌ | ✅ |
| **Compact memory** | ❌ | ✅ |
| **Cross-session recall** | 0% | 95%+ |
| **Token overhead (short)** | Baseline | +50% |
| **Token overhead (long)** | Linear growth | Logarithmic |
| **Compactions** | 0 | Varies |

## Flow Snippets

### Create & Use Baseline Agent
```python
from agent_baseline import BaselineAgent
from config import load_config

config = load_config()
agent = BaselineAgent(config, force_offline=True)

result = agent.reply('user1', 'thread1', 'Hello')
print(result['response'])
print(f"Tokens: {result['token_usage']}")
```

### Create & Use Advanced Agent
```python
from agent_advanced import AdvancedAgent
from config import load_config

config = load_config()
agent = AdvancedAgent(config, force_offline=True)

result = agent.reply('user1', 'thread1', 'Tôi tên là Alice')
result = agent.reply('user1', 'thread2', 'Mình tên gì?')  # Remember!
print(result['response'])  # "Tên bạn là Alice"
```

### Extract Profile Facts
```python
from memory_store import extract_profile_updates

message = "Tôi tên là Alice, ở HCM, là engineer"
facts = extract_profile_updates(message)
# {'name': 'Alice', 'location': 'HCM', 'profession': 'engineer'}
```

### Compact Memory Management
```python
from memory_store import CompactMemoryManager

manager = CompactMemoryManager(
    threshold_tokens=4000,
    keep_messages=10
)

manager.append('thread1', 'user', 'Message 1')
manager.append('thread1', 'assistant', 'Response 1')
# ... many more appends ...
# When total > 4000 tokens, auto-compact!

context = manager.context('thread1')
print(context['summary'])  # Summarized old messages
print(context['messages'])  # Recent messages in full
print(context['compactions'])  # Number of times compacted
```

### Run Benchmark
```python
from benchmark import (
    load_conversations,
    run_agent_benchmark,
    format_rows,
)
from agent_baseline import BaselineAgent
from agent_advanced import AdvancedAgent
from config import load_config
from pathlib import Path

config = load_config(Path('...'))
conversations = load_conversations(config.data_dir / 'conversations.json')

baseline = BaselineAgent(config, force_offline=True)
advanced = AdvancedAgent(config, force_offline=True)

baseline_result = run_agent_benchmark('Baseline', baseline, conversations, config)
advanced_result = run_agent_benchmark('Advanced', advanced, conversations, config)

print(format_rows([baseline_result, advanced_result]))
```

## Profile Fact Extraction Patterns

| Fact Type | Pattern | Example Input |
|-----------|---------|---|
| Name | "tôi tên là" / "mình là" | "Tôi tên là Alice" |
| Location | "ở" / "từ" / "sống ở" | "Mình ở HCM" |
| Profession | "là" / "làm" [job keywords] | "Tôi là engineer" |
| Style | Keywords: ngắn gọn, concise, bullet | "Trả lời ngắn gọn" |
| Favorite drink | "thích" [drink keywords] | "Tôi thích cà phê" |
| Hobbies | "thích" [activity keywords] | "Mình thích chạy bộ" |

## Memory Layer Breakdown

### Layer 1: Short-term (Both agents)
- Where: Memory in RAM (dict of messages)
- Scope: One thread at a time
- Lifetime: Entire conversation in that thread
- Baseline: Lost when thread ends
- Advanced: Kept in CompactMemoryManager

### Layer 2: Persistent (Advanced only)
- Where: Disk file (state/profiles/user_id.md)
- Scope: All threads of one user
- Lifetime: Across all conversations
- Format: Markdown
- Updated: Extract facts from each message

### Layer 3: Compact (Advanced only)
- Where: Summarized text in RAM
- Scope: One thread
- Lifetime: Until next compaction
- Triggered: When total tokens > threshold
- Benefit: Reduces prompt token growth

## Compaction Example

```
BEFORE Compact:
  messages = [
    {role: user, content: "Msg 1..."},      # 100 tokens
    {role: assistant, content: "Resp 1..."}, # 120 tokens
    {role: user, content: "Msg 2..."},      # 110 tokens
    {role: assistant, content: "Resp 2..."}, # 130 tokens
    {role: user, content: "Msg 3..."},      # 100 tokens
    {role: assistant, content: "Resp 3..."}, # 125 tokens
  ]
  summary = ""
  total_tokens = 685

THRESHOLD = 500, KEEP = 2
Threshold exceeded! Trigger compact.

AFTER Compact:
  messages = [
    {role: user, content: "Msg 3..."},      # 100 tokens
    {role: assistant, content: "Resp 3..."}, # 125 tokens
  ]
  summary = """
  ## Conversation Summary (Compacted)
  - User: Msg 1...
  - Assistant: Resp 1...
  - User: Msg 2...
  - Assistant: Resp 2...
  """
  total_tokens = 225 (dropped from 685!)
  compactions = 1
```

## Testing Checklist

- [ ] `test_user_markdown_read_write_edit`: User.md CRUD
- [ ] `test_compact_trigger`: Compaction at threshold
- [ ] `test_cross_session_recall`: Advanced remembers, Baseline forgets
- [ ] `test_compact_reduces_prompt_load_on_long_thread`: Efficiency

## Common Modifications

### Change compaction threshold
```python
# In .env or make_config():
COMPACT_THRESHOLD_TOKENS=2000  # More aggressive
# vs
COMPACT_THRESHOLD_TOKENS=8000  # Less aggressive
```

### Extract more profile facts
```python
# In extract_profile_updates():
# Add regex pattern for new fact type
hobby_match = re.search(r'(thích|yêu)\s+([a-z\s]+)', message, re.IGNORECASE)
if hobby_match:
    updates['hobby'] = hobby_match.group(2)
```

### Better token estimation
```python
# Instead of len(text) // 4, use real tokenizer:
from tiktoken import encoding_for_model
enc = encoding_for_model("gpt-4")
tokens = len(enc.encode(text))
```

### LLM-based summarization
```python
# Instead of heuristic, use LLM:
def summarize_with_llm(messages, llm):
    content = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    response = llm.invoke(f"Summarize: {content}")
    return response.content
```

---

Print this page and keep it nearby while coding! 📋
