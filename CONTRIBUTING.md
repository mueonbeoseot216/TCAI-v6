# Contributing to TCAI v6

Welcome! TCAI is an open-source project, and we welcome contributions.

> ⚠️ **Windows-only project.** TCAI runs on Windows 10/11. If you use Linux:
> - You **can** read code, run `ruff` and `mypy` (static analysis is cross-platform)
> - You **cannot** run the full test suite or the project itself
> - Contributions to platform-agnostic modules (security core, logging, config) are welcome
> - Linux/macOS ports are welcome as future contributions

---

## Development Setup

### Prerequisites
- Windows 10/11
- Python 3.11+
- Git

### Setup

```batch
# Clone
git clone <repo-url>
cd TCAI-v6

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install in development mode with all dev tools
pip install -e ".[dev]"

# Or step by step:
pip install -e .
pip install -r requirements-dev.txt
```

### Verify

```batch
ruff check src/ tests/     # lint
ruff format --check src/   # format check
mypy src/tcai/             # type check
pytest --cov               # run tests
```

---

## Project Structure

```
src/tcai/
├── agent/          # Agent layer (LLM loop, prompts, session management)
├── gateway/        # Security gateway (MCP server, 7-layer pipeline, 35 tools)
│   ├── web/        # Web search module
│   └── tools/      # Diagnostic tools (readonly + write)
└── prompts/        # 5-layer chained prompt system
```

For full architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## How to Contribute

### 1. Find an issue
Check the [Issues](https://github.com/...) tab for open tasks, or open a new one.

### 2. Branch

```batch
git checkout -b feat/my-feature
# or
git checkout -b fix/my-bugfix
```

### 3. Code

Follow [CODING_STANDARDS.md](CODING_STANDARDS.md). Key points:
- All public functions: full type annotations
- Security core modules (`ast_rules`, `deobfuscate`, `injection_filter`, `dlp`): never change logic, only add tests/types
- Use `paths.py` for all file paths (never hardcode strings)
- Use `common.run_cmd()` and `common.decode_output()` for subprocess calls

### 4. Test

```batch
pytest --cov
```

Coverage must not decrease. Target: ≥75% overall, ≥85% for security core.

### 5. Check

```batch
ruff check src/ tests/         # must pass
ruff format --check src/       # must pass
mypy src/tcai/                 # must pass
```

### 6. Commit

Use Conventional Commits:
```
feat(gateway): add new tool
fix(agent): correct learn parsing
test(security): add AST rule tests
docs: update README
```

### 7. Pull Request

Push your branch and open a PR. Fill in the checklist.

---

## What We Need Help With

| Area | Priority |
|------|----------|
| Tests for existing tools | 🔴 High |
| Type annotation completion | 🔴 High |
| Security rule coverage | 🟠 Medium |
| Linux/macOS port | 🟢 Low (not urgent) |
| `rich` UI integration | 🟢 Low |
| Documentation translations | 🟢 Low |

---

## Questions?

Open an issue or discussion. We're happy to help new contributors get started.
