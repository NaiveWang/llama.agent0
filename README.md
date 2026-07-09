# Agent0: Foundational CLI Coding Agent

**Target Scope:** Basic coding tasks, simple scripts, single-file modifications.

**Core Features:**
- Single-file Python CLI script (`agent0.py`).
- Linear `memory.json` chat history for context.
- Command-generation loop with auto-execution via `subprocess.run()`.
- JSON-grammar enforcement for command generation.
- Basic terminal-based interaction.

**Limitations:**
- No direct file read/edit capabilities (relies on shell commands).
- No long-context management (prone to token limits and "lost in the middle").
- No multi-agent parallelism or milestone-based workflows.

---

## Agent0: LLM & Dependency Requirements

### LLM Requirements
- **GBNF (Grammar-Based Next Token Prediction) Support:** To ensure strict JSON-grammar enforcement for command generation, the LLM supports GBNF grammars (e.g., via `llama-cpp-python`) or native JSON mode (e.g., OpenAI's `response_format: { "type": "json_object" }`).
- **Local or API LLM Support:** Compatible with local LLMs served via `llama-cpp-python`/Ollama, or cloud APIs (OpenAI, etc.) with JSON output capabilities.

### Python Library Dependencies
- **Core Dependencies:** `llama-cpp-python` (for local GBNF/grammar enforcement), `requests`, `jsonschema`, `pydantic`.
- **Standard Library Modules:** `json`, `subprocess`, `os`, `typing`.

---

## Agent System Roadmap

- **Agent0**: Foundational CLI Coding Agent (Basic tasks, simple scripts)
- **Agent1**: Next-Gen Single-Agent for Small/Mid Projects & Long Context
- **Agent2**: Multi-Agent Parallel Troubleshooting System for Mid/Large Projects with Web UI & HITL

For detailed requirements:
- [Agent1 Requirements](agent1-requirements.md)
- [Agent2 Requirements Spec](agent2-requirements.md)
