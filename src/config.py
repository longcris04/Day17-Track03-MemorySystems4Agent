from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from model_provider import ProviderConfig


@dataclass
class LabConfig:
    """Đóng gói tất cả cấu hình cho lab.

    Flow: load_config() tạo instance này, sau đó agents sử dụng nó để:
    - Tìm dữ liệu benchmark (data_dir)
    - Lưu trữ persistent memory files (state_dir)
    - Khởi tạo LLM model (model, judge_model)
    - Cấu hình compact memory (threshold_tokens, keep_messages)
    """

    base_dir: Path  # Thư mục gốc của repo
    data_dir: Path  # Thư mục chứa conversations.json, advanced_long_context.json
    state_dir: Path  # Thư mục lưu User.md profiles và trạng thái
    compact_threshold_tokens: int  # Ngưỡng token để kích hoạt compaction
    compact_keep_messages: int  # Số message gần nhất giữ lại khi compact
    model: ProviderConfig  # Config cho agent's main LLM
    judge_model: ProviderConfig  # Config cho LLM dùng để judge chất lượng


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Tải cấu hình từ environment variables.

    Flow:
    1. Xác định repo root (mặc định là parent của src/)
    2. Đọc .env file (nếu có) để tải API keys
    3. Tạo state/ directory nếu chưa tồn tại
    4. Kết hợp env vars + defaults để tạo ProviderConfig
    5. Trả về LabConfig hoàn chỉnh

    Environment variables hỗ trợ:
    - LLM_PROVIDER: Provider sử dụng ('openai', 'anthropic', 'gemini', 'ollama', 'custom', 'openrouter')
    - LLM_MODEL: Model ID (vd: 'gpt-4', 'claude-3-sonnet')
    - LLM_TEMPERATURE: Độ ngẫu nhiên (mặc định 0.3)
    - Provider-specific: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, OLLAMA_BASE_URL, CUSTOM_BASE_URL
    """
    # Xác định repo root: nếu không chỉ định, dùng parent của src/ (tức là repo root)
    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()

    # Thử load .env nếu tồn tại (để lưu credentials locally mà không commit)
    env_file = root / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    # Xác định các thư mục
    data_dir = root / 'data'
    state_dir = root / 'state'

    # Tạo state_dir nếu chưa tồn tại
    state_dir.mkdir(exist_ok=True)

    # Đọc provider settings từ env vars
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    model_name = os.getenv('LLM_MODEL', 'gpt-4-turbo')
    temperature = float(os.getenv('LLM_TEMPERATURE', '0.3'))

    # Build ProviderConfig tùy theo provider
    if provider == 'openai':
        model = ProviderConfig(
            provider='openai',
            model_name=model_name,
            temperature=temperature,
            api_key=os.getenv('OPENAI_API_KEY'),
        )
    elif provider == 'anthropic':
        model = ProviderConfig(
            provider='anthropic',
            model_name=model_name,
            temperature=temperature,
            api_key=os.getenv('ANTHROPIC_API_KEY'),
        )
    elif provider == 'gemini':
        model = ProviderConfig(
            provider='gemini',
            model_name=model_name,
            temperature=temperature,
            api_key=os.getenv('GEMINI_API_KEY'),
        )
    elif provider == 'ollama':
        model = ProviderConfig(
            provider='ollama',
            model_name=model_name,
            temperature=temperature,
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
        )
    elif provider == 'custom':
        model = ProviderConfig(
            provider='custom',
            model_name=model_name,
            temperature=temperature,
            api_key=os.getenv('CUSTOM_API_KEY'),
            base_url=os.getenv('CUSTOM_BASE_URL'),
        )
    elif provider == 'openrouter':
        model = ProviderConfig(
            provider='openrouter',
            model_name=model_name,
            temperature=temperature,
            api_key=os.getenv('OPENROUTER_API_KEY'),
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    # Judge model thường là model giống main model (dùng để đánh giá chất lượng response)
    judge_model = ProviderConfig(
        provider=provider,
        model_name=os.getenv('JUDGE_MODEL', model_name),
        temperature=0.0,  # Judge model luôn deterministic (không ngẫu nhiên)
        api_key=model.api_key,
        base_url=model.base_url,
    )

    # Compact memory settings: kích hoạt khi thread vượt ngưỡng token
    compact_threshold = int(os.getenv('COMPACT_THRESHOLD_TOKENS', '4000'))
    compact_keep = int(os.getenv('COMPACT_KEEP_MESSAGES', '10'))

    return LabConfig(
        base_dir=root,
        data_dir=data_dir,
        state_dir=state_dir,
        compact_threshold_tokens=compact_threshold,
        compact_keep_messages=compact_keep,
        model=model,
        judge_model=judge_model,
    )
