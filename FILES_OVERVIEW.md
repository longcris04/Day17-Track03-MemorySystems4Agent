# 📂 Files Overview

## Source Code (src/)

### 1. **model_provider.py** (95 lines, ~15 min read)
**Purpose**: Abstract different LLM providers into a uniform interface

```python
# Key Classes
ProviderConfig(dataclass)
  - provider: str (openai, anthropic, gemini, ollama, custom, openrouter)
  - model_name: str
  - temperature: float
  - api_key: str | None
  - base_url: str | None

# Key Functions
normalize_provider(value: str) → str
  Purpose: Fix typos ("anthorpic" → "anthropic")
  
build_chat_model(config: ProviderConfig) → ChatModel
  Purpose: Return LangChain ChatModel instance for selected provider
  Flow: provider → ChatOpenAI | ChatAnthropic | ChatGoogleGenerativeAI | ChatOllama | ChatOpenRouter
```

**When to read**: First - foundation for everything
**When to modify**: Adding new LLM provider support
**Dependencies**: None (import only)

---

### 2. **config.py** (120 lines, ~15 min read)
**Purpose**: Load environment variables and create shared configuration object

```python
# Key Class
LabConfig(dataclass)
  - base_dir: Path (repo root)
  - data_dir: Path (benchmark data location)
  - state_dir: Path (where User.md files stored)
  - compact_threshold_tokens: int (when to compact)
  - compact_keep_messages: int (how many to keep)
  - model: ProviderConfig (main LLM)
  - judge_model: ProviderConfig (evaluation LLM)

# Key Function
load_config(base_dir: Path | None) → LabConfig
  Purpose: Read .env file, environment variables, return config
  Handles: Directory creation, provider selection, defaults
```

**When to read**: Second - used by all other files
**When to modify**: Adding new configuration options
**Dependencies**: model_provider.py (ProviderConfig)

---

### 3. **memory_store.py** (320 lines, ~45 min read) ⭐ MOST IMPORTANT
**Purpose**: Core infrastructure for memory management (3 layers)

```python
# Key Functions
estimate_tokens(text: str) → int
  Purpose: Rough token count (len(text) // 4)
  Used for: Checking if compaction needed

extract_profile_updates(message: str) → dict
  Purpose: Parse message for profile facts
  Extracts: name, location, profession, style, favorite_drink, hobbies
  Returns: {'name': 'Alice', 'location': 'HCM', ...}

summarize_messages(messages: list, max_items: int) → str
  Purpose: Create compact summary of old messages
  Used by: CompactMemoryManager during compaction

# Key Classes
UserProfileStore(dataclass)
  Purpose: Persistent User.md file storage
  Methods:
    - path_for(user_id) → Path (sanitized filename)
    - read_text(user_id) → str (file content or default template)
    - write_text(user_id, content) → Path (save to disk)
    - edit_text(user_id, search, replace) → bool (update specific field)
    - file_size(user_id) → int (track memory overhead)

CompactMemoryManager(dataclass)
  Purpose: Automatic message compaction for long threads
  State: dict[thread_id → {messages, summary, compactions}]
  Methods:
    - append(thread_id, role, content) → None (add msg, auto-compact if needed)
    - context(thread_id) → dict (get state: messages+summary)
    - compaction_count(thread_id) → int (how many times compacted)
```

**When to read**: Third - understand all memory operations
**When to modify**: Changing profile facts, compaction logic, token estimation
**Dependencies**: None

---

### 4. **agent_baseline.py** (140 lines, ~20 min read)
**Purpose**: Simple agent with session-only memory (no persistence)

```python
# Key Class
SessionState(dataclass)
  Purpose: Per-thread state
  Fields:
    - messages: list (message history)
    - token_usage: int (output tokens)
    - prompt_tokens_processed: int (input tokens)

BaselineAgent(class)
  Purpose: Stateless across threads, forgets after session ends
  Key Fields:
    - sessions: dict[thread_id → SessionState]
    - langchain_agent: Optional real LLM
  
  Key Methods:
    - reply(user_id, thread_id, message) → dict
      Flow: append user msg → generate response → append to session → track tokens
    
    - token_usage(thread_id) → int (output tokens generated)
    - prompt_token_usage(thread_id) → int (input tokens processed)
    - compaction_count(thread_id) → int (always 0 - no compact memory)
    
    - _reply_offline(thread_id, message) → str
      Deterministic response (no User.md, no memory across threads)
      Returns generic or echo response
```

**When to read**: Fourth - understand simple agent
**When to use**: Short conversations, low cost, single-session interactions
**When to modify**: Changing response generation logic
**Dependencies**: config, memory_store, model_provider

---

### 5. **agent_advanced.py** (220 lines, ~35 min read) ⭐ MOST COMPLEX
**Purpose**: Advanced agent with 3 memory layers

```python
# Key Class
AdvancedAgent(class)
  Purpose: Long-term memory with persistent User.md + compact summarization
  
  Key Fields:
    - profile_store: UserProfileStore (Layer 2 - persistent)
    - compact_memory: CompactMemoryManager (Layer 3 - compact)
    - thread_tokens: dict (track output per thread)
    - thread_prompt_tokens: dict (track input per thread)
  
  Key Methods:
    - reply(user_id, thread_id, message) → dict
      Flow:
        1. Extract profile updates from message
        2. Update User.md with new facts
        3. Append to CompactMemoryManager
        4. Estimate prompt context tokens
        5. Generate smart response (using User.md)
        6. Append response to CompactMemoryManager
        7. Track tokens and return
    
    - token_usage(thread_id) → int
    - prompt_token_usage(thread_id) → int
    - memory_file_size(user_id) → int (User.md size)
    - compaction_count(thread_id) → int
    
    - _reply_offline(user_id, thread_id, message) → dict
      1. Extract profile facts
      2. Update User.md
      3. Append to compact memory
      4. Estimate tokens
      5. Generate smart response
      6. Return result
    
    - _offline_response(user_id, thread_id, message) → str
      Parses User.md to answer recall questions:
      - "Mình tên gì?" → Extract name from User.md
      - "Mình ở đâu?" → Extract location from User.md
      - "Mình làm gì?" → Extract profession from User.md
      Generic response if not recall question
    
    - _estimate_prompt_context_tokens(user_id, thread_id) → int
      Sum tokens: User.md + summary + recent messages
```

**When to read**: Fifth - understand advanced agent
**When to use**: Long conversations, need long-term memory, cross-session recall
**When to modify**: Profile extraction, response generation, memory layers
**Dependencies**: config, memory_store, model_provider

---

### 6. **benchmark.py** (300 lines, ~40 min read)
**Purpose**: Compare agents on datasets with multiple metrics

```python
# Key Classes
BenchmarkRow(dataclass)
  Purpose: One agent's benchmark results
  Fields:
    - agent_name: str
    - agent_tokens_only: int (output tokens)
    - prompt_tokens_processed: int (input tokens)
    - recall_score: float (0-1, accuracy on recall questions)
    - response_quality: float (0-1, heuristic quality score)
    - memory_growth_bytes: int (User.md final size)
    - compactions: int (times memory was compacted)

# Key Functions
load_conversations(path: Path) → list[dict]
  Purpose: Load JSON conversation data
  Format: [{id, user_id, turns[], recall_questions[]}]

recall_points(answer: str, expected: list[str]) → float
  Purpose: Score recall accuracy
  Returns: 1.0 (all facts present), 0.5 (partial), 0.0 (none)

heuristic_quality(answer: str, expected: list[str]) → float
  Purpose: Quality score (length + recall + repetition)
  Returns: 0.0-1.0

run_agent_benchmark(agent_name, agent, conversations, config) → BenchmarkRow
  Purpose: Benchmark one agent
  Flow:
    1. Feed all conversation turns to agent
    2. Track agent tokens + prompt tokens
    3. Ask recall questions in fresh thread
    4. Score answers
    5. Record memory + compaction metrics

format_rows(rows: list[BenchmarkRow]) → str
  Purpose: Print results as markdown table

main() → None
  Purpose: Run full benchmark
  Flow:
    1. Load 2 datasets (standard + long-context)
    2. Initialize Baseline + Advanced
    3. Run benchmark on each dataset
    4. Print results + analysis
```

**When to read**: Sixth - understand evaluation
**When to run**: `python benchmark.py` (no args needed)
**When to modify**: Adding new metrics, changing datasets
**Dependencies**: agent_baseline, agent_advanced, config, memory_store

---

### 7. **test_agents.py** (200 lines, ~30 min read)
**Purpose**: Unit tests for core functionality

```python
# Key Functions
make_config(tmp_path: Path) → LabConfig
  Purpose: Create isolated test config
  Sets: state_dir=tmp_path, low thresholds for fast tests

test_user_markdown_read_write_edit(tmp_path: Path) → None
  Tests:
    1. Read default template (new user)
    2. Write custom content
    3. Edit specific fields
    4. Verify changes persisted
    5. Check file_size

test_compact_trigger(tmp_path: Path) → None
  Tests:
    1. Append messages until exceeding threshold
    2. Verify compaction_count > 0
    3. Check summary was created

test_cross_session_recall(tmp_path: Path) → None
  Tests:
    1. Session 1: Share name
    2. Session 2 (fresh thread): Ask name
    3. Baseline: Forgets (no name in response)
    4. Advanced: Remembers (name in response)

test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) → None
  Tests:
    1. Feed long conversation (10+ turns)
    2. Compare prompt tokens
    3. Verify Advanced has compactions
```

**When to read**: Last - understand testing approach
**When to run**: `python -m pytest test_agents.py -v`
**When to modify**: Adding new test cases
**Dependencies**: agent_baseline, agent_advanced, config

---

## Data Files (data/)

### conversations.json
**Purpose**: Standard benchmark dataset (realistic multi-turn conversations)
**Format**: JSON array of conversations
**Size**: 5 conversations, ~50 total turns
**Content**: Vietnamese dialog with user "dungct" sharing profile facts
**Recall questions**: Each conversation has 1-2 recall questions testing memory

```json
[
  {
    "id": "conv-01",
    "user_id": "dungct",
    "turns": ["Chào bạn, mình tên là DũngCT.", ...],
    "recall_questions": [
      {"question": "Mình tên gì?", "expected_contains": ["DũngCT"]}
    ]
  },
  ...
]
```

**Usage**: `load_conversations(config.data_dir / 'conversations.json')`

---

### advanced_long_context.json
**Purpose**: Stress test for long conversations and compaction
**Format**: Same JSON format as conversations.json
**Size**: 1 conversation, 21 turns (deliberately long)
**Content**: Vietnamese dialog with multiple topics, corrections, noise
**Special features**:
  - Location update (Đà Nẵng → Huế → Đà Nẵng)
  - Multiple news topics (Artemis III, X-59, El Niño, BC energy)
  - Distraction facts (Hà Nội, Huế mentioned but not final locations)
  - 3 recall questions testing memory + noise filtering

**Usage**: `load_conversations(config.data_dir / 'advanced_long_context.json')`

**Expected behavior**:
- Baseline: Low recall (~5%), high token usage (~15000)
- Advanced: High recall (~95%), medium token usage (~8000) thanks to compaction

---

## Documentation Files

### IMPLEMENTATION_GUIDE.md (Comprehensive)
**Length**: ~400 lines
**Time to read**: 60-90 minutes
**Content**:
- Architecture overview with diagrams
- File-by-file implementation summary
- Data format examples
- Complete flow example with pseudocode
- Expected benchmark results
- Key insights and trade-offs

**Recommended reading order**:
1. Read for architecture understanding
2. Reference while studying source code
3. Review when designing modifications

---

### FLOW_DIAGRAM.md (Visual)
**Length**: ~300 lines
**Time to read**: 30-45 minutes
**Content**:
- ASCII diagrams of complete flows
- Baseline vs Advanced comparison
- Compact memory algorithm with examples
- Token growth visualization
- Layer-by-layer breakdown

**Best for**:
- Visual learners
- Understanding trade-offs
- Explaining to others

---

### QUICKSTART.md (Practical)
**Length**: ~200 lines
**Time to read**: 15-20 minutes
**Content**:
- Environment setup (5 min)
- API key configuration (5 min)
- Quick test examples (5 min)
- How to run benchmark (3 min)
- How to run tests (2 min)
- FAQ with common questions

**Start here**: For hands-on learning

---

### QUICK_REFERENCE.md (Cheat Sheet)
**Length**: ~200 lines
**Time to read**: 5-10 minutes (as reference)
**Content**:
- Class hierarchies
- Function signatures
- Environment variables
- Agent comparison table
- Code snippets
- Memory layer breakdown

**Use as**: Quick lookup while coding

---

### COMPLETION_SUMMARY.md (This File)
**Length**: ~300 lines
**Time to read**: 20-30 minutes
**Content**:
- What was implemented (checklist)
- Key features summary
- Expected benchmark results
- How to run code
- Learning outcomes
- Integration points
- Limitations & future work

**Use for**: Project overview

---

### FILES_OVERVIEW.md (Navigation)
**This file!**
**Purpose**: Understand what's in each file
**Use for**: Deciding what to read next

---

## Reading Paths (Recommended)

### Path 1: Quick Understanding (30 min)
1. QUICKSTART.md (15 min)
2. QUICK_REFERENCE.md (10 min)
3. Run `python benchmark.py` (5 min)

### Path 2: Deep Understanding (180 min)
1. QUICKSTART.md (15 min)
2. agent_baseline.py (20 min)
3. agent_advanced.py (35 min)
4. memory_store.py (45 min)
5. IMPLEMENTATION_GUIDE.md (40 min)
6. Run tests & benchmark (25 min)

### Path 3: Complete Mastery (360+ min)
1. All of Path 2
2. FLOW_DIAGRAM.md (40 min)
3. Read all source code line-by-line (120 min)
4. Modify code and experiment (120+ min)

### Path 4: Just Get It Running (10 min)
1. QUICKSTART.md - Setup
2. Run `python benchmark.py`

---

## File Dependencies

```
model_provider.py
  ├─ (no imports from project)
  
config.py
  ├─ model_provider.py

memory_store.py
  ├─ (no imports from project)

agent_baseline.py
  ├─ config.py
  ├─ memory_store.py (only estimate_tokens)
  ├─ model_provider.py (indirect via config)

agent_advanced.py
  ├─ config.py
  ├─ memory_store.py (all of it)
  ├─ model_provider.py (indirect via config)

benchmark.py
  ├─ config.py
  ├─ memory_store.py (for metrics)
  ├─ agent_baseline.py
  ├─ agent_advanced.py
  
test_agents.py
  ├─ config.py
  ├─ agent_baseline.py
  ├─ agent_advanced.py
```

**Import order**: model_provider → config → memory_store → agents → benchmark/tests

---

## File Sizes & Complexity

| File | Lines | Complexity | Time | Dependencies |
|------|-------|-----------|------|---|
| model_provider.py | 95 | ⭐ | 15 min | 0 |
| config.py | 120 | ⭐ | 15 min | 1 |
| memory_store.py | 320 | ⭐⭐⭐ | 45 min | 0 |
| agent_baseline.py | 140 | ⭐⭐ | 20 min | 3 |
| agent_advanced.py | 220 | ⭐⭐⭐⭐ | 35 min | 3 |
| benchmark.py | 300 | ⭐⭐ | 40 min | 4 |
| test_agents.py | 200 | ⭐⭐ | 30 min | 3 |

Total: ~1400 lines of code, ~3-4 hours to fully understand

---

## Quick Navigation

**"How do I..."**

- ...run the code? → QUICKSTART.md
- ...understand what each file does? → This file
- ...see the architecture? → FLOW_DIAGRAM.md
- ...understand memory layers? → IMPLEMENTATION_GUIDE.md
- ...set environment variables? → QUICK_REFERENCE.md
- ...debug a feature? → QUICK_REFERENCE.md (Common Modifications)
- ...add a new provider? → model_provider.py + IMPLEMENTATION_GUIDE.md
- ...extract new profile facts? → memory_store.py (extract_profile_updates)
- ...change compaction? → config.py + memory_store.py (CompactMemoryManager)
- ...understand metrics? → benchmark.py (BenchmarkRow)

---

**Start with QUICKSTART.md, then come back here when you need to navigate!** 🚀
