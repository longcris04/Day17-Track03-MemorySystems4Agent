from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    """Trạng thái của một session trong một thread.

    Flow: BaselineAgent giữ session state per thread_id để remember messages
    trong cùng một thread, nhưng QUÊN khi sang thread mới.

    Mục đích: Theo dõi messages + token usage của thread này.
    """
    messages: list[dict[str, str]] = field(default_factory=list)  # [{"role": "user", "content": "..."}, ...]
    token_usage: int = 0  # Số token mà agent đã generate (output tokens)
    prompt_tokens_processed: int = 0  # Tổng prompt tokens (messages * conversation count)


class BaselineAgent:
    """Agent baseline với chỉ short-term memory (trong cùng thread).

    Flow:
    1. Mỗi thread_id có một SessionState riêng
    2. reply() thêm user message vào session, generate response
    3. Khi sang thread_id khác, tạo SessionState mới → quên thread cũ
    4. Không bao giờ lưu User.md, không compact memory

    Mục đích so sánh: Baseline đơn giản, dùng để compare token cost vs Advanced.
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}  # thread_id → SessionState

        # Optional: initialize real LangChain agent nếu dependencies tồn tại
        self.langchain_agent = None
        if not force_offline:
            try:
                self._maybe_build_langchain_agent()
            except Exception:
                # Fallback to offline nếu LLM API unavailable
                pass

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Xử lý user message và trả về response.

        Flow:
        1. Kiểm tra nếu thread_id chưa tồn tại → tạo SessionState mới
        2. Append user message vào session.messages
        3. Gọi _reply_offline() (hoặc LLM nếu có) để generate response
        4. Append response vào session.messages
        5. Trả về {'response': '...', 'token_usage': X, 'prompt_tokens': Y}

        user_id: Unused in baseline (vì không lưu User.md)
        thread_id: Session key (mỗi thread quên thread khác)
        """
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()

        session = self.sessions[thread_id]

        # Thêm user message vào session
        session.messages.append({'role': 'user', 'content': message})

        # Generate response
        if self.langchain_agent and not self.force_offline:
            # Live path: gọi real LLM (nếu implement)
            response = self._reply_live(thread_id, message)
        else:
            # Offline path: deterministic response
            response = self._reply_offline(thread_id, message)

        # Thêm response vào session
        session.messages.append({'role': 'assistant', 'content': response})

        # Tính token usage (heuristic)
        response_tokens = estimate_tokens(response)
        session.token_usage += response_tokens

        # Tính prompt tokens: sum của tất cả messages đã process
        session.prompt_tokens_processed = sum(
            estimate_tokens(msg['content']) for msg in session.messages
        )

        return {
            'response': response,
            'token_usage': response_tokens,
            'prompt_tokens_processed': session.prompt_tokens_processed,
        }

    def token_usage(self, thread_id: str) -> int:
        """Tổng token mà agent đã generate trên thread này.

        Mục đích: Benchmark đo lường output token cost.
        """
        if thread_id not in self.sessions:
            return 0
        return self.sessions[thread_id].token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        """Tổng prompt token mà agent đã process trên thread này.

        Mục đích: Benchmark đo lường context cost (input tokens).
        """
        if thread_id not in self.sessions:
            return 0
        return self.sessions[thread_id].prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        """Baseline không có compact memory → luôn 0."""
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> str:
        """Generate deterministic response khi không có real LLM.

        Flow:
        - Không dùng any persistent memory (User.md)
        - Trả lời generic hoặc based on current session messages
        - Nếu user hỏi về profile facts (tên, nghề, etc.) → "I don't remember"

        Mục đích: Cho phép benchmark chạy offline mà không cần API keys.
        """
        # Kiểm tra nếu user hỏi "nhắc lại" (recall question)
        if any(keyword in message.lower() for keyword in ['nhắc lại', 'tên gì', 'nghề gì', 'ở đâu', 'mình là gì']):
            # Baseline không nhớ facts across threads
            return "Xin lỗi, mình chỉ nhớ messages trong conversation hiện tại. Nếu bạn nói về điều này ở conversation khác, mình sẽ quên."

        # Generic response
        session = self.sessions.get(thread_id, SessionState())
        if len(session.messages) == 1:
            # Lần đầu → welcome message
            return "Xin chào! Mình là Baseline Agent. Tôi chỉ nhớ messages trong conversation này. Mỗi conversation mới, tôi sẽ quên mọi thứ. Bạn cần gì giúp không?"
        else:
            # Follow-up → echo-like response
            return f"Hiểu rồi. Cảm ơn bạn đã chia sẻ: '{message[:50]}...'. Có gì khác mình giúp không?"

    def _reply_live(self, thread_id: str, message: str) -> str:
        """Generate response từ real LLM.

        Gửi toàn bộ session history (đã có current user message) lên LLM.
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        session = self.sessions[thread_id]

        lc_messages = [SystemMessage(content=(
            "You are a helpful assistant. "
            "You remember messages within this conversation but forget everything "
            "when the conversation ends. Reply concisely."
        ))]

        for msg in session.messages:
            if msg['role'] == 'user':
                lc_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                lc_messages.append(AIMessage(content=msg['content']))

        result = self.langchain_agent.invoke(lc_messages)
        return result.content

    def _maybe_build_langchain_agent(self):
        """Optional: khởi tạo real LangChain agent nếu dependencies tồn tại.

        Flow:
        1. Gọi build_chat_model(self.config.model) để get chat model
        2. (Optional) Wrap với InMemorySaver, tools, etc.
        3. Set self.langchain_agent = agent

        Mục đích: Cho phép upgrade từ offline to live khi API khả dụng.
        """
        try:
            self.langchain_agent = build_chat_model(self.config.model)
        except Exception:
            # Nếu build_chat_model fail (e.g., missing API key), fall back to offline
            self.langchain_agent = None
