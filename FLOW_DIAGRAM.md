# Memory Systems Flow Diagram

## 🎯 Main Agent Flow

```
User Message Input
        ↓
    agent.reply(user_id, thread_id, message)
        ↓
    ┌────────────────────────────────────────────────────┐
    │           BASELINE AGENT                            │
    │                                                      │
    │  1. Get or Create SessionState[thread_id]          │
    │     └─ messages: []                                │
    │     └─ token_usage: 0                              │
    │                                                      │
    │  2. Append user message                            │
    │     messages.append({'role': 'user', content})     │
    │                                                      │
    │  3. Generate Response (offline)                    │
    │     └─ NO access to User.md                        │
    │     └─ Only uses messages in this thread           │
    │     └─ Generic or echo response                    │
    │                                                      │
    │  4. Track Tokens                                    │
    │     └─ token_usage += estimate_tokens(response)    │
    │     └─ prompt_tokens = sum(all messages)           │
    │                                                      │
    │  5. Return                                          │
    │     {'response': '...', 'token_usage': X, ...}    │
    └────────────────────────────────────────────────────┘
        ↓
    Session-specific memory
    (Forget when thread_id changes)
```

## 🧠 Advanced Agent Flow (3 Memory Layers)

```
User Message Input
        ↓
    agent.reply(user_id, thread_id, message)
        ↓
    ┌────────────────────────────────────────────────────┐
    │         ADVANCED AGENT: LAYER 1 - SHORT-TERM       │
    │                                                      │
    │  Get or Initialize CompactMemoryManager state      │
    │    for this thread_id                              │
    └────────────────────────────────────────────────────┘
        ↓
    ┌────────────────────────────────────────────────────┐
    │         ADVANCED AGENT: LAYER 2 - PERSISTENT       │
    │                                                      │
    │  1. Extract Profile Updates from Message           │
    │     extract_profile_updates(message)               │
    │     → {'name': 'Alice', 'location': 'HCM', ...}   │
    │                                                      │
    │  2. Update User.md File                            │
    │     profile_store.read_text(user_id)               │
    │     └─ Read current profile                        │
    │     profile_store.edit_text(...)                   │
    │     └─ Update with new facts                       │
    │                                                      │
    │  User.md Template:                                  │
    │  ┌─────────────────────────────────┐              │
    │  │ # User Profile: alice           │              │
    │  │                                  │              │
    │  │ ## Personal Information           │              │
    │  │ - Name: Alice                    │              │
    │  │ - Location: HCM                  │              │
    │  │ - Profession: Engineer           │              │
    │  │                                  │              │
    │  │ ## Preferences                    │              │
    │  │ - Response style: concise        │              │
    │  │ - Favorite drink: coffee         │              │
    │  └─────────────────────────────────┘              │
    └────────────────────────────────────────────────────┘
        ↓
    ┌────────────────────────────────────────────────────┐
    │         ADVANCED AGENT: LAYER 3 - COMPACT          │
    │                                                      │
    │  1. Append User Message                            │
    │     compact_memory.append(thread_id, 'user', msg)  │
    │     └─ Adds to messages list                       │
    │                                                      │
    │  2. Check: Total Tokens > Threshold?               │
    │     IF total_tokens > compact_threshold_tokens:    │
    │        ↓                                            │
    │        Compact Old Messages:                        │
    │        - Summarize oldest messages                 │
    │        - Keep only last `keep_messages` in full    │
    │        - Replace with [summary] + [recent]         │
    │        - Increment compaction_count                │
    │                                                      │
    │        Before Compact:                              │
    │        messages = [msg1, msg2, msg3, msg4, msg5]   │
    │        summary = ""                                │
    │                                                      │
    │        After Compact (keep_messages=2):            │
    │        messages = [msg4, msg5]                     │
    │        summary = "[Summary of msg1-msg3]"          │
    │                                                      │
    │  3. Estimate Prompt Context Tokens                 │
    │     tokens = estimate_tokens(User.md) +            │
    │              estimate_tokens(summary) +            │
    │              sum(estimate_tokens(msg) for msg      │
    │                  in recent_messages)               │
    │                                                      │
    │     This represents input token cost                │
    └────────────────────────────────────────────────────┘
        ↓
    ┌────────────────────────────────────────────────────┐
    │         GENERATE SMART RESPONSE                     │
    │                                                      │
    │  _offline_response(user_id, thread_id, message)    │
    │                                                      │
    │  1. Read User.md (persistent facts)                │
    │  2. Check if message is recall question:           │
    │                                                      │
    │     "Mình tên gì?"                                 │
    │     → Extract from User.md: "- Name: Alice"        │
    │     → Response: "Tên bạn là Alice."               │
    │                                                      │
    │     "Mình ở đâu?"                                  │
    │     → Extract from User.md: "- Location: HCM"      │
    │     → Response: "Bạn ở HCM."                      │
    │                                                      │
    │     "Mình thích gì?"                               │
    │     → Extract from User.md: "- Favorite drink: ..." │
    │     → Response: "Bạn thích ..."                   │
    │                                                      │
    │  3. If not recall question, generic response       │
    │                                                      │
    │  4. Track response quality:                         │
    │     - heuristic_quality(answer)                    │
    │     - recall_points(answer, expected_facts)        │
    └────────────────────────────────────────────────────┘
        ↓
    ┌────────────────────────────────────────────────────┐
    │         FINALIZE & TRACK                           │
    │                                                      │
    │  1. Append Assistant Response to Compact Memory    │
    │     compact_memory.append(thread_id, 'assistant',  │
    │                           response)                 │
    │                                                      │
    │  2. Update Token Counters                          │
    │     token_usage[thread_id] += estimate_tokens(...)│
    │     prompt_tokens[thread_id] += prompt_context... │
    │                                                      │
    │  3. Return Result                                   │
    │     {                                              │
    │       'response': 'Tên bạn là Alice.',            │
    │       'token_usage': 15,                           │
    │       'prompt_tokens_processed': 250,              │
    │     }                                              │
    └────────────────────────────────────────────────────┘
```

## 📊 Compact Memory Algorithm

```
Thread State:
  messages = [msg1, msg2, msg3, msg4, msg5, msg6, msg7]
  summary = ""
  compactions = 0
  
Total tokens = 500 + 600 + 550 + ... = 3500

User appends new message (size 400 tokens):
  messages = [msg1, msg2, msg3, msg4, msg5, msg6, msg7, NEW_MSG]
  Total tokens = 3900 (still < 4000 threshold)
  
User appends another message (size 200 tokens):
  messages = [msg1, msg2, msg3, msg4, msg5, msg6, msg7, NEW_MSG, NEW_MSG2]
  Total tokens = 4100
  
THRESHOLD EXCEEDED (4100 > 4000)!
    ↓
Trigger Compaction:
  1. Split messages:
     old_messages = [msg1, msg2, msg3, msg4, msg5, msg6, msg7]
     recent_messages = [NEW_MSG, NEW_MSG2]
     
  2. Summarize old messages:
     summary = """
     ## Conversation Summary (Compacted)
     - msg1: user asked about ...
     - msg2: assistant replied with ...
     - msg3: user shared ...
     - ...
     """
     
  3. Replace state:
     messages = [NEW_MSG, NEW_MSG2]  (recent only)
     summary = (as above)
     compactions = 1

Result: Next turn, prompt will be:
  [User.md] + [Summary] + [NEW_MSG, NEW_MSG2]
  Instead of: [msg1...msg7, NEW_MSG, NEW_MSG2]
  
  This significantly reduces input tokens for long threads!
```

## 🎯 Baseline vs Advanced Comparison

```
Session 1: "Tôi tên là Alice"
Session 2: "Mình tên gì?"

BASELINE AGENT:
  Session 1, thread="conv1":
    └─ SessionState[conv1].messages = [msg1]
    └─ Response: "Đã ghi nhớ"
    
  Session 2, thread="conv2":
    └─ SessionState[conv2] = NEW state (conv1 forgotten!)
    └─ Response: "Xin lỗi, tôi không nhớ"
    └─ Recall: 0%
    
ADVANCED AGENT:
  Session 1, thread="conv1":
    └─ User.md: "- Name: Alice"
    └─ CompactMemory[conv1]: [msg1]
    └─ Response: "Đã ghi nhớ"
    
  Session 2, thread="conv2":
    └─ User.md: Still has "- Name: Alice"
    └─ CompactMemory[conv2]: [new msg]
    └─ Extract from User.md → Response: "Tên bạn là Alice"
    └─ Recall: 100%
```

## 📈 Token Growth Over Conversation

```
SHORT CONVERSATION (10 turns):

Baseline:
  Turn 1: prompt_tokens = 100  (just msg1)
  Turn 2: prompt_tokens = 200  (msg1 + msg2)
  ...
  Turn 10: prompt_tokens = 1000 (msg1-10)
  Total prompt = 5500 tokens
  
Advanced:
  Turn 1: prompt_tokens = 150  (User.md=50 + msg1=100)
  Turn 2: prompt_tokens = 250  (User.md=50 + msg1-2=200)
  ...
  Turn 10: prompt_tokens = 1050 (User.md=50 + msg1-10=1000)
  Total prompt = 5750 tokens
  → Advanced is HIGHER on short conversations (User.md overhead)


LONG CONVERSATION (50 turns):

Baseline (no compaction):
  Turn 1-30: prompt grows linearly
  Turn 31: prompt_tokens = 3100
  Turn 40: prompt_tokens = 4000
  Turn 50: prompt_tokens = 5000
  Total prompt = 125000 tokens (explodes!)
  
Advanced (with compaction at 4000 threshold):
  Turn 1-40: prompt grows like baseline
  Turn 41: Compaction triggered!
    └─ Summarize turn 1-35
    └─ Keep turn 36-40 in full
    └─ New prompt = 200 + 500 = 700 (massive drop!)
  Turn 42-50: prompt stays ~800-1000
  Total prompt = 35000 tokens
  → Advanced is MUCH LOWER on long conversations!
  
SAVINGS = (125000 - 35000) / 125000 = 72% fewer prompt tokens!
```

---

Mình hy vọng diagrams này giúp bạn hiểu rõ flow! 🚀
