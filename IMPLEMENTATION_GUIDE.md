# Memory Systems for AI Agents - Implementation Guide

## Overview

Bài lab này xây dựng 2 agents để so sánh cách manage memory:
- **Baseline Agent**: Chỉ nhớ messages trong thread hiện tại (quên khi sang thread mới)
- **Advanced Agent**: Nhớ lâu dài thông qua 3 memory layers

## Architecture Overview

```
User Input
    ↓
Agent.reply(user_id, thread_id, message)
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: SHORT-TERM MEMORY                                      │
│ - Messages trong thread hiện tại                                 │
│ - SessionState (Baseline) hoặc CompactMemoryManager (Advanced)  │
│ - Quên khi sang thread mới (Baseline)                            │
│ - Keep recent messages trong compact state (Advanced)            │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: PERSISTENT MEMORY (Advanced only)                       │
│ - User.md file per user (stable facts)                           │
│ - Name, location, profession, preferences                        │
│ - Extract từ messages, update incrementally                      │
│ - Survive across sessions/threads                                │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: COMPACT MEMORY (Advanced only)                          │
│ - Summarize old messages khi thread > threshold                  │
│ - Keep recent messages in full                                   │
│ - Reduce prompt token growth on long threads                     │
│ - Track compaction count                                         │
└─────────────────────────────────────────────────────────────────┘
    ↓
LLM Response
    ↓
Update counters + persist memory
```

## File-by-File Implementation Summary

### 1. **model_provider.py** - LLM Provider Abstraction
**Mục đích**: Cho phép agents chạy với bất kỳ LLM provider nào.

**Key functions**:
- `normalize_provider()`: Fix typo ("anthorpic" → "anthropic")
- `build_chat_model()`: Khởi tạo ChatModel tùy theo provider
  - openai → ChatOpenAI
  - gemini → ChatGoogleGenerativeAI
  - anthropic → ChatAnthropic
  - ollama → ChatOllama
  - custom → ChatOpenAI with base_url
  - openrouter → ChatOpenRouter

**Flow**:
```
ProviderConfig → build_chat_model() → LangChain ChatModel object
```

### 2. **config.py** - Configuration Management
**Mục đích**: Load env vars và tạo shared config cho cả 2 agents.

**Key class**:
- `LabConfig`: Đóng gói toàn bộ settings (paths, model, compact thresholds)
- `load_config()`: Đọc từ environment variables

**Env vars hỗ trợ**:
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=...
COMPACT_THRESHOLD_TOKENS=4000
COMPACT_KEEP_MESSAGES=10
```

**Flow**:
```
Environment → load_config() → LabConfig → agents
```

### 3. **memory_store.py** - Memory Management Core
**Mục đích**: Cơ sở hạ tầng cho 3 memory layers.

**Key functions**:

#### a. `estimate_tokens(text)`
- Ước tính tokens (heuristic: len(text) // 4)
- Dùng để kiểm tra khi nào compact

#### b. `UserProfileStore` - Persistent Memory
```python
# Read User.md hiện tại (hoặc default template)
profile = store.read_text(user_id)

# Write User.md toàn bộ
store.write_text(user_id, new_content)

# Update một field cụ thể
store.edit_text(user_id, 'Name: (unknown)', 'Name: Alice')

# Kiểm tra memory overhead
size = store.file_size(user_id)
```

#### c. `extract_profile_updates(message)`
- Parse message để trích facts
- Tìm: tên, địa chỉ, nghề, style trả lời, sở thích
- Dùng regex patterns
- Return dict: {'name': 'Alice', 'location': 'HCM', ...}

#### d. `CompactMemoryManager` - Compact Memory
```python
manager = CompactMemoryManager(threshold_tokens=4000, keep_messages=10)

# Append message, auto-trigger compaction nếu vượt ngưỡng
manager.append(thread_id, 'user', 'message')

# Get current state (summary + recent messages)
context = manager.context(thread_id)
# Returns: {'messages': [...], 'summary': '...', 'compactions': 2}

# Track compactions for benchmarking
count = manager.compaction_count(thread_id)
```

**Compact Logic**:
```
Total tokens > threshold
    ↓
Tóm tắt old messages → summary
Keep recent `keep_messages` in full
Replace full messages with [summary] + [recent messages]
Increment compaction counter
```

### 4. **agent_baseline.py** - Baseline Agent (Short-term Only)
**Mục đích**: Simple agent to compare against Advanced.

**Architecture**:
```python
BaselineAgent:
  - sessions: dict[thread_id → SessionState]
  - SessionState: {messages[], token_usage, prompt_tokens_processed}
  
reply(user_id, thread_id, message):
  → Look up or create SessionState for thread_id
  → Append user message
  → Generate response (offline deterministic)
  → Track token usage
  → Return response
```

**Key behaviors**:
- Mỗi thread có separate SessionState (không share across threads)
- Quên messages từ thread cũ khi sang thread mới
- Không lưu User.md
- Không compact memory
- `_reply_offline()`: Generate generic responses (không dùng persistent memory)

**Token tracking**:
- `token_usage()`: Output tokens mà agent generated
- `prompt_token_usage()`: Tổng input tokens processed

### 5. **agent_advanced.py** - Advanced Agent (3 Layers)
**Mục đích**: Agent với long-term memory + efficiency.

**Architecture**:
```python
AdvancedAgent:
  - profile_store: UserProfileStore (Layer 2)
  - compact_memory: CompactMemoryManager (Layer 3)
  - thread_tokens, thread_prompt_tokens: tracking
  
reply(user_id, thread_id, message):
  ↓
  1. Extract profile facts từ message
  ↓
  2. Update User.md với facts mới
  ↓
  3. Append message → compact_memory
  ↓
  4. Estimate prompt tokens (User.md + summary + recent messages)
  ↓
  5. Generate response (có thể dùng User.md để trả lời recall questions)
  ↓
  6. Append response → compact_memory
  ↓
  7. Track tokens + return response
```

**Key methods**:

#### `_reply_offline(user_id, thread_id, message)`
- Extract profile updates
- Update User.md
- Append to compact memory
- Generate smart response (dùng persistent memory)

#### `_estimate_prompt_context_tokens(user_id, thread_id)`
- Sum tokens: User.md + summary + recent messages
- Đo input token cost

#### `_offline_response(user_id, thread_id, message)`
- Parse User.md để trả lời recall questions
- "Mình tên gì?" → Extract name từ User.md
- "Mình ở đâu?" → Extract location từ User.md
- Generic responses nếu không có recall question

**Recall Question Handling**:
```python
# User.md format:
# - Name: Alice
# - Location: HCM
# - Profession: Software Engineer

# Khi hỏi "Mình tên gì?"
→ Parse "- Name: Alice"
→ Trả lời "Tên bạn là Alice"
```

### 6. **benchmark.py** - Benchmark Framework
**Mục đích**: So sánh 2 agents trên datasets.

**Flow**:
```
Load conversations
    ↓
┌─────────────────────────────────────────────────────┐
│ For each agent (Baseline, Advanced):                 │
│  1. Feed all conversation turns                      │
│  2. Track agent tokens + prompt tokens               │
│  3. Ask recall questions in fresh thread             │
│  4. Score answers (recall_points, heuristic_quality) │
│  5. Record memory size + compaction count            │
└─────────────────────────────────────────────────────┘
    ↓
Output BenchmarkRow for each agent
    ↓
Format + display results
```

**Key metrics**:
- **Agent tokens only**: Output tokens generated (response cost)
- **Prompt tokens processed**: Input tokens (context cost)
- **Recall score**: % of expected facts in answer (0.0, 0.5, 1.0)
- **Response quality**: Heuristic quality score
- **Memory growth**: Final User.md size
- **Compactions**: # of times compaction happened

**Recall scoring**:
```python
recall_points(answer, ['fact1', 'fact2']):
  → Check if 'fact1' and 'fact2' in answer
  → Return 1.0 (all), 0.5 (partial), 0.0 (none)
```

**Heuristic quality**:
- Length score: 20-500 chars is good
- Recall score: from recall_points()
- Repetition score: avoid excessive word repetition
- Weighted average: 30% length + 50% recall + 20% repetition

### 7. **test_agents.py** - Unit Tests
**Mục đích**: Verify core functionality.

**Tests**:

#### `test_user_markdown_read_write_edit()`
- Create User.md
- Read default template
- Write custom content
- Edit specific fields
- Verify file_size()

#### `test_compact_trigger()`
- Append messages until threshold exceeded
- Verify compaction_count > 0
- Check context has summary

#### `test_cross_session_recall()`
- Session 1: Share name in thread_1
- Session 2: Ask name in thread_2 (fresh)
- Baseline: Forget (no "Alice")
- Advanced: Remember (has "Alice")

#### `test_compact_reduces_prompt_load_on_long_thread()`
- Create long conversation (10 turns)
- Compare prompt_tokens between agents
- Advanced should have compaction
- Verify compaction_count > 0

## Data Format

### conversations.json
```json
[
  {
    "id": "conv-01",
    "user_id": "dungct",
    "turns": [
      "Tôi tên là DũngCT",
      "Tôi ở Đà Nẵng",
      "Tôi là backend engineer",
      "..."
    ],
    "recall_questions": [
      {
        "question": "Mình tên gì?",
        "expected_contains": ["DũngCT"]
      }
    ]
  }
]
```

### advanced_long_context.json
```json
[
  {
    "id": "stress-01",
    "user_id": "dungct_stress",
    "turns": [
      "Long message 1",
      "Long message 2",
      "..."  // 21 turns total
    ],
    "recall_questions": [
      {
        "question": "Mình tên gì và ở đâu?",
        "expected_contains": ["DũngCT Stress", "Đà Nẵng"]
      }
    ]
  }
]
```

## Running the Implementation

### Option 1: Run Benchmark
```bash
cd src
python benchmark.py
```
Output: Comparison table showing metrics for both agents.

### Option 2: Run Tests
```bash
cd src
python -m pytest test_agents.py -v
```
Output: Test results showing memory functionality works.

### Option 3: Run Individual Agent
```bash
python -c "
from agent_baseline import BaselineAgent
from config import load_config

config = load_config()
agent = BaselineAgent(config, force_offline=True)
result = agent.reply('user123', 'thread1', 'Xin chào!')
print(result['response'])
"
```

## Expected Benchmark Results

### Standard Benchmark (short conversations)
```
| Agent    | Agent Tokens | Prompt Tokens | Recall | Quality | Memory | Compactions |
|----------|---------|------------|--------|---------|--------|-------------|
| Baseline | 500     | 800        | 0%     | 0.65    | 0      | 0           |
| Advanced | 480     | 1200       | 95%    | 0.90    | 2500   | 0           |
```
- Advanced has more prompt tokens (User.md overhead) but MUCH higher recall
- No compaction on short conversations

### Long-Context Stress (21-turn conversation)
```
| Agent    | Agent Tokens | Prompt Tokens | Recall | Quality | Memory | Compactions |
|----------|---------|------------|--------|---------|--------|-------------|
| Baseline | 2100    | 15000      | 5%     | 0.40    | 0      | 0           |
| Advanced | 2050    | 8000       | 95%    | 0.88    | 8000   | 3-5         |
```
- Baseline's prompt tokens explode (all messages in context)
- Advanced uses compaction to keep prompt tokens manageable
- Advanced recall remains high despite compaction

## Key Insights

1. **Short-term vs Long-term trade-off**
   - Baseline: Simple, low overhead on short conversations
   - Advanced: Higher overhead but scales better on long conversations

2. **Compaction is critical**
   - On short conversations: Not needed
   - On long conversations: Reduces prompt token explosion

3. **Recall as metric**
   - Baseline: Always low (forgets facts)
   - Advanced: High (persistent User.md)
   - Compaction doesn't affect recall (summary is for efficiency, not accuracy)

4. **Memory growth**
   - User.md stays small (only stable facts)
   - Compact memory summary replaces old messages (no explosion)
   - Overall memory overhead is manageable

## Pseudocode: Complete Flow Example

```python
# Setup
config = load_config()
advanced = AdvancedAgent(config, force_offline=True)

# Session 1
result1 = advanced.reply('alice', 'conv1', 'Tôi tên là Alice')
# → extract_profile_updates: {'name': 'Alice'}
# → update User.md: "- Name: Alice"
# → append to compact_memory
# → response: "Vâng, đã ghi nhớ tên Alice."

result2 = advanced.reply('alice', 'conv1', 'Tôi ở HCM')
# → extract_profile_updates: {'location': 'HCM'}
# → update User.md: "- Location: HCM"
# → append to compact_memory
# → response: "Vâng, đã ghi nhớ Alice ở HCM."

# Session 2 (fresh thread, Baseline would forget)
result3 = advanced.reply('alice', 'conv2', 'Mình tên gì?')
# → read User.md: "- Name: Alice"
# → extract profile updates: none (question-only)
# → append to compact_memory
# → _offline_response: See "Name: Alice" in User.md
# → response: "Tên bạn là Alice."

# Benchmark
baseline = BaselineAgent(config, force_offline=True)
# Same Session 1 turns...
result3_baseline = baseline.reply('alice', 'conv2', 'Mình tên gì?')
# → No User.md to consult
# → _reply_offline: Generic response (no recall)
# → response: "Xin lỗi, mình chỉ nhớ conversation hiện tại."

# Advanced recall: 100%
# Baseline recall: 0%
```

---

Good luck! 🚀 Bây giờ bạn đã có complete implementation với comments chi tiết. Chạy `python benchmark.py` để thấy kết quả!
