from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    """Kết quả benchmark cho một agent trên một dataset.

    Flow: Benchmark tính toán các metrics này cho mỗi agent, rồi so sánh.

    Metrics:
    - agent_tokens_only: Output tokens mà agent sinh ra (không count input)
    - prompt_tokens_processed: Input tokens (messages + context) mà agent phải xử lý
    - recall_score: Độ chính xác trả lời recall questions (0.0-1.0)
    - response_quality: Chất lượng chung của responses (heuristic 0.0-1.0)
    - memory_growth_bytes: Tổng kích thước User.md (đo lường memory overhead)
    - compactions: Số lần thread bị compact memory (efficiency metric)
    """
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Đọc JSON conversations từ disk.

    Format expected:
    [
      {
        "id": "conv-01",
        "user_id": "dungct",
        "turns": ["message1", "message2", ...],
        "recall_questions": [
          {"question": "...", "expected_contains": ["fact1", "fact2"]}
        ]
      },
      ...
    ]

    Mục đích: Load dataset benchmark vào memory để test agents.
    """
    if not path.exists():
        raise FileNotFoundError(f"Conversation file not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    """Tính recall score dựa trên presence của expected facts.

    Flow: Sau khi agent trả lời recall question, kiểm tra xem
    expected facts có xuất hiện trong answer hay không.

    Scoring:
    - 1.0: Tất cả expected facts có mặt (complete recall)
    - 0.5: Một nửa expected facts có mặt (partial recall)
    - 0.0: Không fact nào có mặt (no recall)

    Mục đích: Định lượng khả năng nhớ lâu dài của agent.
    """
    if not expected:
        return 1.0  # No facts to check

    answer_lower = answer.lower()
    matches = 0

    for fact in expected:
        # Tìm fact trong answer (case-insensitive)
        if fact.lower() in answer_lower:
            matches += 1

    # Scoring heuristic
    match_ratio = matches / len(expected)
    if match_ratio == 1.0:
        return 1.0  # All facts present
    elif match_ratio >= 0.5:
        return 0.5  # Partial
    else:
        return 0.0  # None or too few


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Lightweight quality score cho offline mode.

    Flow: Không có real LLM judge, nên dùng heuristics:
    - Độ dài (answers quá ngắn hoặc quá dài → quality thấp)
    - Presence of expected facts (recall score)
    - Lack of gibberish/repetition

    Mục đích: Approximate response quality khi offline.
    """
    if not answer or len(answer.strip()) == 0:
        return 0.0

    # Factor 1: Length heuristic (expected ~50-300 chars)
    length = len(answer.strip())
    length_score = 1.0 if 20 <= length <= 500 else 0.5

    # Factor 2: Recall score (recall_points already checks for expected facts)
    recall_score = recall_points(answer, expected)

    # Factor 3: No extreme repetition (detect if same word repeated >5 times)
    words = answer.split()
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    max_freq = max(word_freq.values()) if word_freq else 0
    repetition_score = 1.0 if max_freq < 5 else 0.7

    # Weighted average
    quality = (length_score * 0.3 + recall_score * 0.5 + repetition_score * 0.2)
    return min(quality, 1.0)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Đánh giá một agent trên dataset conversations.

    Flow:
    1. Loop qua mỗi conversation
    2. Cho mỗi turn, gọi agent.reply(user_id, thread_id, message)
    3. Track agent tokens, prompt tokens per turn
    4. Sau khi xong tất cả turns, gọi recall questions trên fresh thread
    5. Tính average recall score + quality score
    6. Record memory file size + compaction count

    Mục đích: Benchmark agent trên cùng dataset để fair comparison.
    """
    total_agent_tokens = 0
    total_prompt_tokens = 0
    recall_scores = []
    quality_scores = []
    max_memory_size = 0
    total_compactions = 0

    # Feed all conversation turns to agent
    for conversation in conversations:
        user_id = conversation['user_id']
        thread_id = conversation['id']

        for turn_msg in conversation['turns']:
            result = agent.reply(user_id, thread_id, turn_msg)
            total_agent_tokens += result.get('token_usage', 0)
            total_prompt_tokens += result.get('prompt_tokens_processed', 0)

        # After conversation, ask recall questions in a FRESH thread (test cross-session recall)
        fresh_thread_id = f"{thread_id}_recall"

        for recall_item in conversation.get('recall_questions', []):
            question = recall_item['question']
            expected = recall_item.get('expected_contains', [])

            # Ask question in fresh thread
            result = agent.reply(user_id, fresh_thread_id, question)
            answer = result['response']

            # Score this answer
            recall = recall_points(answer, expected)
            quality = heuristic_quality(answer, expected)

            recall_scores.append(recall)
            quality_scores.append(quality)

        # Record memory metrics
        if isinstance(agent, AdvancedAgent):
            memory_size = agent.memory_file_size(user_id)
            max_memory_size = max(max_memory_size, memory_size)

            compaction_count = agent.compaction_count(thread_id)
            total_compactions = max(total_compactions, compaction_count)
        else:
            max_memory_size = 0
            total_compactions = 0  # Baseline không có compact

    # Average scores
    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=max_memory_size,
        compactions=total_compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Format benchmark results thành markdown table.

    Flow: Pretty-print results để dễ so sánh giữa agents.
    """
    try:
        from tabulate import tabulate

        data = []
        for row in rows:
            data.append([
                row.agent_name,
                row.agent_tokens_only,
                row.prompt_tokens_processed,
                f"{row.recall_score:.2%}",
                f"{row.response_quality:.2%}",
                row.memory_growth_bytes,
                row.compactions,
            ])

        headers = [
            'Agent',
            'Agent Tokens',
            'Prompt Tokens',
            'Recall Score',
            'Response Quality',
            'Memory (bytes)',
            'Compactions',
        ]

        return tabulate(data, headers=headers, tablefmt='grid')
    except ImportError:
        # Fallback nếu không có tabulate
        lines = ['| Agent | Tokens | Prompt Tokens | Recall | Quality | Memory | Compactions |']
        lines.append('|-------|--------|---------------|--------|---------|--------|-------------|')
        for row in rows:
            lines.append(
                f'| {row.agent_name} | {row.agent_tokens_only} | {row.prompt_tokens_processed} | '
                f'{row.recall_score:.2%} | {row.response_quality:.2%} | {row.memory_growth_bytes} | {row.compactions} |'
            )
        return '\n'.join(lines)


def main() -> None:
    """Chạy full benchmark suite.

    Flow:
    1. Load config
    2. Load cả 2 datasets (standard + long-context stress)
    3. Initialize Baseline và Advanced agents
    4. Run benchmark trên mỗi dataset
    5. Print comparison tables

    Mục đích: Hiển thị trade-off giữa Baseline (simple) và Advanced (memory layers).
    """
    config = load_config(Path(__file__).resolve().parent.parent)

    # Load datasets
    standard_conversations = load_conversations(config.data_dir / 'conversations.json')
    long_context_conversations = load_conversations(config.data_dir / 'advanced_long_context.json')

    print("=" * 80)
    print("MEMORY SYSTEMS FOR AI AGENTS - BENCHMARK RESULTS")
    print("=" * 80)
    print()

    # Benchmark 1: Standard conversations
    print("### Standard Benchmark (data/conversations.json)")
    print()

    baseline = BaselineAgent(config, force_offline=False)
    advanced = AdvancedAgent(config, force_offline=False)

    baseline_result = run_agent_benchmark('Baseline', baseline, standard_conversations, config)
    advanced_result = run_agent_benchmark('Advanced', advanced, standard_conversations, config)

    print(format_rows([baseline_result, advanced_result]))
    print()

    # Benchmark 2: Long-context stress
    print("### Long-Context Stress Benchmark (data/advanced_long_context.json)")
    print()

    baseline2 = BaselineAgent(config, force_offline=False)
    advanced2 = AdvancedAgent(config, force_offline=False)

    baseline_result2 = run_agent_benchmark('Baseline', baseline2, long_context_conversations, config)
    advanced_result2 = run_agent_benchmark('Advanced', advanced2, long_context_conversations, config)

    print(format_rows([baseline_result2, advanced_result2]))
    print()

    # Analysis
    print("### Analysis")
    print()
    print("**Standard Benchmark:**")
    print(f"- Baseline: {baseline_result.agent_tokens_only} agent tokens, {baseline_result.prompt_tokens_processed} prompt tokens, {baseline_result.recall_score:.0%} recall")
    print(f"- Advanced: {advanced_result.agent_tokens_only} agent tokens, {advanced_result.prompt_tokens_processed} prompt tokens, {advanced_result.recall_score:.0%} recall")
    print()
    print("**Long-Context Stress Benchmark:**")
    print(f"- Baseline: {baseline_result2.agent_tokens_only} agent tokens, {baseline_result2.prompt_tokens_processed} prompt tokens, {baseline_result2.recall_score:.0%} recall")
    print(f"- Advanced: {advanced_result2.agent_tokens_only} agent tokens, {advanced_result2.prompt_tokens_processed} prompt tokens, {advanced_result2.recall_score:.0%} recall")
    print()
    print("**Key Insights:**")
    print("1. Baseline forgetting across sessions (low recall) but simpler context")
    print("2. Advanced remembers profile (high recall) but builds larger User.md")
    print("3. On long threads, compact memory should help Advanced reduce prompt tokens")
    print("4. Trade-off: Long-term memory cost vs. improved accuracy on recall questions")


if __name__ == "__main__":
    main()
