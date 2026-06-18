# Student Scaffold

This `src/` folder is the student version of the lab.

- It mirrors the working implementation in `labs/`
- It keeps the same high-level structure
- The Python files are intentionally incomplete and contain pseudocode / TODOs
- The benchmark structure should stay the same as `labs/`: standard benchmark + long-context stress benchmark
- The runtime should support the same providers as `labs/`: `openai`, `custom`, `gemini`, `anthropic`, `ollama`, `openrouter`

Suggested flow:

1. Start with `config.py`
2. Implement `memory_store.py`
3. Finish `agent_baseline.py`
4. Finish `agent_advanced.py`
5. Implement `benchmark.py`
6. Make `test_agents.py` pass

Datasets are available at the repo root in `data/`.
