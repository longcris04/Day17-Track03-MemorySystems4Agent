from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Đóng gói cấu hình cho các LLM provider khác nhau.

    Flow: Khi agent cần gọi LLM, nó truyền ProviderConfig vào build_chat_model()
    để lấy được chat model object phù hợp với provider.

    Hỗ trợ 6 provider:
    - openai: Sử dụng API key từ OpenAI
    - custom: OpenAI-compatible endpoint (tự deploy hoặc third-party)
    - gemini: Google Generative AI
    - anthropic: Anthropic Claude
    - ollama: Local LLM server
    - openrouter: OpenRouter API gateway
    """

    provider: str  # Tên provider: 'openai', 'gemini', 'anthropic', etc.
    model_name: str  # Model ID: 'gpt-4', 'claude-3-sonnet', etc.
    temperature: float  # Độ ngẫu nhiên của response (0.0 = deterministic, 1.0 = creative)
    api_key: str | None = None  # API key nếu cần (OpenAI, Gemini, Anthropic, etc.)
    base_url: str | None = None  # Base URL cho custom endpoint hoặc ollama


def normalize_provider(value: str) -> str:
    """Sửa lỗi typo phổ biến trong tên provider.

    Flow: Người dùng có thể nhập sai (e.g., 'anthorpic' thay vì 'anthropic').
    Hàm này chuẩn hóa trước khi truyền vào build_chat_model().
    """
    # Mapping các typo phổ biến thành tên đúng
    aliases = {
        'anthorpic': 'anthropic',
        'claude': 'anthropic',
        'openai_compatible': 'custom',
        'ollama_local': 'ollama',
    }
    normalized = value.lower().strip()
    return aliases.get(normalized, normalized)


def build_chat_model(config: ProviderConfig):
    """Khởi tạo chat model tương ứng với provider.

    Flow:
    1. Nhận ProviderConfig từ config.py
    2. Dựa trên tên provider, import + khởi tạo LangChain chat model
    3. Trả về model object có thể gọi được (model(messages) → response)

    Ví dụ:
    - Nếu config.provider = 'openai', khởi tạo ChatOpenAI với api_key
    - Nếu config.provider = 'custom', khởi tạo ChatOpenAI với base_url
    - Nếu config.provider = 'ollama', khởi tạo ChatOllama với base_url
    """
    provider = normalize_provider(config.provider)

    if provider == 'openai':
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
        )

    elif provider == 'custom':
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key or 'dummy-key',
            base_url=config.base_url,
        )

    elif provider == 'gemini':
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            temperature=config.temperature,
            google_api_key=config.api_key,
        )

    elif provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
        )

    elif provider == 'ollama':
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=config.model_name,
            temperature=config.temperature,
            base_url=config.base_url or 'http://localhost:11434',
        )

    elif provider == 'openrouter':
        from langchain_openrouter import ChatOpenRouter
        return ChatOpenRouter(
            model=config.model_name,
            temperature=config.temperature,
            openrouter_api_key=config.api_key,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")
