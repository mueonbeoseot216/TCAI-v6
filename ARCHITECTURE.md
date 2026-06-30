# TCAI v6 — Architecture

> This document will be updated as modules are migrated from v5.
> For the v5 architecture, see `E:\tcai_v5\ARCHITECTURE.md`.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   TCAI v6                           │
│                                                     │
│  ┌──────────────┐     stdio JSON-RPC    ┌─────────┐ │
│  │  Agent Layer │ ◄──────────────────► │ Gateway │ │
│  │              │                      │  Layer  │ │
│  │  main.py     │                      │ server  │ │
│  │  loop.py     │                      │ gateway │ │
│  │  learn.py    │                      │ router  │ │
│  │  mcp_client  │                      │ tools/  │ │
│  │  prompt_*    │                      │ web/    │ │
│  │  knowledge   │                      │ audit   │ │
│  │  session     │                      │ ...     │ │
│  │  ui          │                      │         │ │
│  └──────────────┘                      └─────────┘ │
│                                                     │
│  Dependencies: pyyaml, python-dotenv (core)         │
│  Optional: httpx, beautifulsoup4, rich              │
└─────────────────────────────────────────────────────┘
```

## Package Layout

```
src/tcai/
├── agent/          # Agent — LLM interaction, user interface
│   ├── main.py         Entry point, command routing
│   ├── loop.py         LLM call loop, tool orchestration
│   ├── learn.py        /learn knowledge extraction
│   ├── mcp_client.py   stdio JSON-RPC client
│   ├── prompt_engine.py 5-layer chained prompts
│   ├── prompt_gate.py  Zero-token security monitor
│   ├── knowledge.py    SQLite FTS5 knowledge base
│   ├── session.py      Session recording
│   └── ui.py           Terminal UI
│
├── gateway/        # Gateway — security pipeline + tools
│   ├── paths.py            All project paths (from __file__)
│   ├── config.py           Centralized configuration
│   ├── exceptions.py       Custom exception hierarchy
│   ├── logging_setup.py    Structured logging
│   ├── http_client.py      Unified HTTP client
│   ├── server.py           MCP JSON-RPC main loop + routing
│   ├── tool_registry.py    Schema collection from tools
│   ├── gateway.py          6-step security pipeline orchestrator
│   ├── scope_checker.py    Path scope validation
│   ├── session_context.py  Unified session state + approvals
│   ├── ast_rules.py        AST rule engine
│   ├── deobfuscate.py      4-stage deobfuscation
│   ├── injection_filter.py Injection detection + chunked filtering
│   ├── dlp.py              Data leak prevention
│   ├── circuit_breaker.py  4D circuit breaker
│   ├── audit.py            JSONL audit logging
│   ├── knowledge_bridge.py Cross-layer knowledge access
│   ├── web/                Web search module
│   │   ├── search_engine.py
│   │   └── content_extractor.py
│   └── tools/              Diagnostic tools (31)
│       ├── common.py       Shared run_cmd / decode_output
│       ├── readonly/       21 read-only tools
│       └── write/          10 write tools
│
└── prompts/         # 5-layer chained prompt texts
```

## Data Flow

```
User Input
    │
    ▼
AgentLoop.run()
    │
    ├── knowledge.search()        # FTS5 full-text search
    │
    ├── _call_llm()               # DeepSeek API
    │       │
    │       ▼
    │   LLM Response (may include tool_calls)
    │       │
    │       ├── Tool Call → mcp_client.call_tool()
    │       │       │
    │       │       ▼
    │       │   Gateway.handle_tool_call()
    │       │       │
    │       │       ├── tool_loop_guard.check()
    │       │       ├── [readonly] → dlp.check() → execute
    │       │       └── [write] → 6-step pipeline → execute
    │       │
    │       └── Final Text → session.record() → UI.response()
    │
    └── repeat until no more tool_calls
```

## Security Pipeline (write tools)

```
handle_write()
    │
    ├── 1. Scope Check      → path in allowed scope?
    ├── 2. Deobfuscation     → 4-stage normalization
    ├── 3. AST Rules         → allowlist/blocklist match
    ├── 4. Intent Chain      → cross-session attack pattern?
    ├── 5. Circuit Breaker   → rate/block/reject/score check
    └── 6. Dispatch          → SAFE execute / RISKY approve / BLOCKED reject
            │
            ▼
        audit.log (JSONL append-only)
```
