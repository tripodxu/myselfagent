# MySelfAgent - LangChain Agent Learning Project

> **Version**: v1.3.0
> **Status**: First version, not manually verified. Features added incrementally, README updated同步
> **Last updated**: 2026-08-29

---

## Project Overview

A LangChain-based Agent system built with **TDD (Test-Driven Development)**.

Four core modules: **LLM** (decision maker) / **Tools** (executor) / **Memory** (persistence) / **Planner** (goal decomposition).

### Workflow

```
Goal -> Plan -> LLM decides tool -> Execute -> Store result in memory -> LLM re-evaluates -> ... -> Task complete
```

### Architecture

```
                    +---------------------------+
                    |         Agent Core         |
                    |   (plan->decide->execute   |
                    |    ->evaluate->loop)       |
                    +---+-------+-------+-------+
                        |       |       |
               +--------+--+ +--+---+ +-+--------+
               | LLM Planner| | Tools| | Context  |
               | (decompose | | JSON | | Manager  |
               |  evaluate  | |Schema| | (tokens, |
               |  replan)   | +--+---+ | compress)|
               +--------+--+    |      +----------+
                        |   +---+----+
                    +---+---+---+ +--+-------+
                    |python_exec| |BufferMem |
                    |file_io    | |(persist) |
                    |search     | +----------+
                    |datetime   |
                    +-----------+
```

---

## Quick Start

### 1. Setup

```bash
git clone https://github.com/tripodxu/myselfagent.git
cd myselfagent
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` to `.env` and edit. Requires a local LLM API compatible with OpenAI responses format.

Default: `http://127.0.0.1:8788/v1/responses` with model `oxx`.

### 3. Run

```bash
# Single task
python main.py "What is today's date?"

# Interactive mode
python main.py --interactive

# Debug mode (see LLM streaming output, tool calls, timestamps)
python main.py --interactive --debug
```

### 4. Test

```bash
pytest -v                    # All tests
pytest --cov=src             # With coverage
pytest tests/test_llm.py     # Specific module
python examples/full_test.py # Full feature test (10 tests)
```

---

## Project Structure

```
myselfagent/
├── main.py                    # Entry point
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── src/
│   ├── llm.py                 # LLM module (streaming, retry, reasoning effort)
│   ├── agent.py               # Agent core (layered messages, safety review)
│   ├── tools/
│   │   ├── base.py            # BaseTool + ToolRegistry (JSON Schema support)
│   │   ├── python_exec.py     # Safe Python execution
│   │   ├── file_io.py         # File read/write/list
│   │   ├── search.py          # Text/file search (regex)
│   │   └── datetime_tool.py   # Date/time with Chinese date support
│   ├── memory/
│   │   ├── base.py            # BaseMemory
│   │   ├── buffer.py          # BufferMemory (JSON persistence)
│   │   └── context_manager.py # Context window manager
│   └── planner/
│       ├── llm_planner.py     # LLM-driven planner (decompose/evaluate/replan)
│       └── simple.py          # Simple planner (fallback)
├── tests/                     # 104 tests, all passing
└── examples/
    ├── demo.py
    └── full_test.py           # 10 comprehensive feature tests
```

---

## Module Details

### LLM Module (src/llm.py)

- **Streaming**: Real-time SSE parsing, chunks printed in debug mode
- **Retry**: Exponential backoff (1s, 2s, 4s)
- **Reasoning effort**: Auto-adjusts (low/medium/high) based on task complexity
- **Fallback**: Streaming -> sync if stream returns empty

### Tool System (src/tools/)

Each tool has `parameters_schema()` returning JSON Schema for precise LLM tool selection:

- **python_exec**: Safe code execution, blocks dangerous imports (subprocess, socket, etc.)
- **file_io**: Read/write/list with path whitelist security
- **search**: Regex search in text or files
- **datetime**: Current date/time, relative dates (+N, tomorrow, etc.)

### Memory System (src/memory/)

- **BufferMemory**: Message list with max_size, JSON file persistence
- **ContextManager**: Token tracking, auto-compression, tool output truncation

### Planner (src/planner/)

- **LLMPlanner**: LLM decomposes goal into steps, evaluates each result, supports dynamic replan
- **SimplePlanner**: Goal as single step, used as fallback

### Agent Core (src/agent.py)

Three-phase LLM loop:

```
Phase 1: LLM decomposes goal -> ["step1", "step2", "step3"]
Phase 2: Loop {
    LLM decides tool (with layered messages: developer/user/assistant history)
    Safety review (blocks dangerous patterns)
    Execute tool
    LLM evaluates result -> continue / stop / replan
}
Phase 3: Select best result
```

### Debug Mode

```
[20:52:42.265] [GOAL] Goal: analyze files
[20:52:42.265] [CONFIG] Reasoning effort: medium
[20:52:42.265] [PLAN] Plan created: 3 steps
[20:52:42.938] [ITER] Iter 1: Step 1
[20:52:42.938] [DECIDE] Deciding...
[20:52:42.940] [MSG] [DEVELOPER] You are an AI agent...
[20:52:42.941] [MSG] [USER] Goal: analyze files
[20:52:42.942] [API_REQ] Full prompt sent to LLM
{"tool":"python_exec","params":{"code":"..."}}    <- streaming output
[20:52:43.100] [API_RES] LLM response complete (85 chars)
[20:52:43.100] [SAFETY] Safety: ok
[20:52:43.101] [EXEC] Executing...
[20:52:43.150] [RESULT] Result: {"success": true, "output": "..."}
[20:52:43.151] [EVAL] Eval: stop - goal achieved
[20:52:43.152] [CTX] Context: 450 tokens, 15% used
[20:52:43.152] [DONE] Done: 0.89s, 1 iters
```

---

## Test Statistics

| Module | Tests | Coverage |
|--------|-------|----------|
| LLM | 6 | init, call, retry, timeout, streaming |
| Tool base | 10 | registry, schema, get/list |
| Python exec | 8 | execution, errors, security |
| File IO | 8 | read, write, list, permissions |
| Search | 11 | text, file, regex, filters |
| Memory base | 7 | add, get, clear, search, summary |
| Buffer memory | 9 | store, retrieve, persistence, max_size |
| Context manager | 11 | tokens, compression, truncation, stats |
| LLM Planner | 15 | create, evaluate, replan, fallback |
| Simple Planner | 9 | create, update, complete, progress |
| Agent | 10 | init, cycle, errors, memory, safety |

**Total: 104 tests, all passing**

---

## Changelog

### v1.3.0 - Context Management (2026-08-29)

- `ContextManager`: token tracking, auto-compression, tool output truncation
- System messages always preserved in context window
- Budget-aware context retrieval
- Debug mode shows context utilization

### v1.2.0 - Codex-Inspired Optimizations (2026-08-29)

- JSON Schema tool definitions (`parameters_schema()`)
- Layered message system (developer / user / assistant)
- Safety review layer (blocks dangerous patterns before execution)
- Reasoning effort control (auto low/medium/high)

### v1.1.0 - LLM Planner (2026-08-29)

- `LLMPlanner`: LLM decomposes goal, evaluates results, dynamic replan
- Agent loop: plan -> decide -> execute -> evaluate (continue/stop/replan)
- 15 new planner tests

### v1.0.1 - Bug Fixes (2026-08-29)

Fixed 6 critical bugs:
1. **Encoding crash**: `sys.stdout.reconfigure()` instead of replacing stream
2. **Agent won't stop**: `has_answer()` early termination
3. **No feedback**: Prior results passed to LLM
4. **Fake planner**: Goal as single step instead of fixed 5 generic steps
5. **No backoff**: Exponential retry (1s, 2s, 4s)
6. **Wrong result**: `select_best_result()` picks richest answer

### v1.0.0 - Initial Release (2026-08-29)

- Project structure, TDD approach
- LLM, tools, memory, planner, agent core
- 78 tests passing

---

## Roadmap

1. Vector memory (long-term storage)
2. Web search integration
3. Multi-agent collaboration
4. Web UI
5. More tools (database, API calls)

---

> **Note**: This is a learning project. Code not manually verified. Features added incrementally.
