from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class AgentContext:
    """Context cho mỗi user-thread pair."""
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Agent với 3 memory layers: short-term + persistent + compact.

    Flow:
    1. Short-term: Messages trong thread hiện tại (SessionState)
    2. Persistent: User.md file (facts, profile, preferences)
    3. Compact: Long thread → summarize old messages, keep recent messages

    Mục đích: Nhớ lâu dài + efficient context trên long threads.
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline

        # Layer 2: Persistent memory - User.md per user
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")

        # Layer 3: Compact memory for long threads
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )

        # Token tracking per thread
        self.thread_tokens: dict[str, int] = {}  # thread_id → cumulative output tokens
        self.thread_prompt_tokens: dict[str, int] = {}  # thread_id → cumulative prompt tokens

        # Optional: real LangChain agent
        self.langchain_agent = None
        if not force_offline:
            try:
                self._maybe_build_langchain_agent()
            except Exception:
                pass

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Xử lý user message và trả về response với 3 memory layers.

        Flow:
        1. Gọi _reply_offline (hoặc live LLM)
        2. Hàm này:
           - Extract profile updates từ message
           - Update User.md
           - Append vào compact memory
           - Estimate prompt tokens (including User.md + summary)
           - Generate response
           - Track token usage
        3. Return {'response': '...', 'token_usage': X, 'prompt_tokens': Y}
        """
        if self.langchain_agent and not self.force_offline:
            result = self._reply_live(user_id, thread_id, message)
        else:
            result = self._reply_offline(user_id, thread_id, message)

        return result

    def token_usage(self, thread_id: str) -> int:
        """Tổng output tokens mà agent generated trên thread này."""
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        """Tổng prompt tokens (input context) processed trên thread này."""
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        """Kích thước User.md của user (bytes).

        Mục đích: Benchmark đo memory growth.
        """
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        """Số lần compact memory đã thực hiện trên thread này."""
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Deterministic advanced response với 3 memory layers.

        Flow:
        1. Extract profile facts từ incoming message
        2. Update User.md với facts mới
        3. Append user message vào compact memory
        4. Estimate prompt context (User.md + summary + recent messages)
        5. Generate response có thể trả lời recall questions
        6. Append response vào compact memory
        7. Track tokens

        Mục đích: Cho phép offline benchmark mà vẫn test long-term memory.
        """
        # Step 1: Extract profile updates
        updates = extract_profile_updates(message)

        # Step 2: Update User.md with new facts
        if updates:
            profile_text = self.profile_store.read_text(user_id)
            for key, value in updates.items():
                # Update profile (simple heuristic: replace old value with new)
                if key == 'name':
                    self.profile_store.edit_text(user_id, '- Name: (unknown)', f'- Name: {value}')
                elif key == 'location':
                    self.profile_store.edit_text(user_id, '- Location: (unknown)', f'- Location: {value}')
                elif key == 'profession':
                    self.profile_store.edit_text(user_id, '- Profession: (unknown)', f'- Profession: {value}')
                # ... add more mappings as needed

        # Step 3: Append message to compact memory
        self.compact_memory.append(thread_id, 'user', message)

        # Step 4: Estimate prompt context tokens
        prompt_context_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_context_tokens

        # Step 5: Generate response (using persisted memory)
        response = self._offline_response(user_id, thread_id, message)

        # Step 6: Append response to compact memory
        self.compact_memory.append(thread_id, 'assistant', response)

        # Step 7: Update token usage
        response_tokens = estimate_tokens(response)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + response_tokens

        return {
            'response': response,
            'token_usage': response_tokens,
            'prompt_tokens_processed': prompt_context_tokens,
        }

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Live path: gọi real LLM với memory tools (optional)."""
        # Placeholder: khi implement với LangChain tools
        return self._reply_offline(user_id, thread_id, message)

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Ước tính prompt tokens cho turn này.

        Components:
        1. User.md file size
        2. Compact memory summary size
        3. Recent kept messages size
        4. Prompt engineering overhead

        Mục đích: Theo dõi input token cost (có thể cao trên long threads).
        """
        tokens = 0

        # User.md tokens
        profile_text = self.profile_store.read_text(user_id)
        tokens += estimate_tokens(profile_text)

        # Compact memory context tokens
        context = self.compact_memory.context(thread_id)
        if context.get('summary'):
            tokens += estimate_tokens(context['summary'])
        if context.get('messages'):
            for msg in context['messages']:
                tokens += estimate_tokens(msg.get('content', ''))

        # Overhead for system prompts, formatting
        tokens += 50

        return tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Generate response dùng persisted memory (User.md + compact history).

        Mục đích: Cho phép Advanced agent trả lời recall questions như:
        - "Mình tên gì?"
        - "Hiện tại mình làm nghề gì?"
        - "Nhắc lại style trả lời mình thích"

        Flow:
        1. Đọc User.md để lấy profile facts
        2. Kiểm tra nếu user hỏi recall question
        3. Extract answer từ User.md (hoặc compact history)
        4. Generate response
        """
        # Đọc profile
        profile_text = self.profile_store.read_text(user_id)
        context_state = self.compact_memory.context(thread_id)

        # Kiểm tra recall questions
        lower_msg = message.lower()

        # "Mình tên gì?" / "Tôi tên gì?"
        if any(kw in lower_msg for kw in ['tên gì', 'tên của mình', 'tên tôi']):
            if '- Name:' in profile_text:
                # Extract name từ "- Name: XYZ"
                import re
                match = re.search(r'- Name:\s*(.+)', profile_text)
                if match:
                    name = match.group(1).strip()
                    if name != '(unknown)':
                        return f"Tên bạn là {name}."
            return "Bạn chưa nói tên. Bạn tên gì?"

        # "Mình làm nghề gì?" / "Hiện tại mình làm gì?"
        if any(kw in lower_msg for kw in ['nghề gì', 'làm gì', 'công việc gì', 'profession']):
            if '- Profession:' in profile_text:
                import re
                match = re.search(r'- Profession:\s*(.+)', profile_text)
                if match:
                    profession = match.group(1).strip()
                    if profession != '(unknown)':
                        return f"Bạn là một {profession}."
            return "Bạn chưa nói về công việc. Bạn làm gì?"

        # "Mình ở đâu?" / "Địa chỉ?"
        if any(kw in lower_msg for kw in ['ở đâu', 'địa chỉ', 'location', 'sống ở']):
            if '- Location:' in profile_text:
                import re
                match = re.search(r'- Location:\s*(.+)', profile_text)
                if match:
                    location = match.group(1).strip()
                    if location != '(unknown)':
                        return f"Bạn ở {location}."
            return "Bạn chưa nói về địa chỉ. Bạn sống ở đâu?"

        # "Nhắc lại style trả lời"
        if 'style' in lower_msg or 'trả lời' in lower_msg:
            if '- Response style:' in profile_text:
                import re
                match = re.search(r'- Response style:\s*(.+)', profile_text)
                if match:
                    style = match.group(1).strip()
                    if style != '(learning)':
                        return f"Style trả lời bạn thích: {style}"
            return "Bạn chưa nói về style trả lời bạn thích."

        # Generic response
        if len(context_state['messages']) == 1:
            return "Xin chào! Mình là Advanced Agent. Mình nhớ profile bạn và lịch sử chat qua many sessions. Bạn cần gì giúp không?"
        else:
            return f"Cảm ơn bạn chia sẻ: '{message[:40]}...'. Mình đã lưu thông tin này vào profile của bạn."

    def _maybe_build_langchain_agent(self):
        """Optional: khởi tạo real LangChain agent với tools.

        Design:
        - build_chat_model() để get base LLM
        - Tools: read_user_profile(), update_user_profile()
        - InMemorySaver cho thread state
        - Dynamic system prompt inject User.md

        Mục đích: Advanced path khi LLM API khả dụng.
        """
        try:
            self.langchain_agent = build_chat_model(self.config.model)
        except Exception:
            self.langchain_agent = None
