# TCAI v6 — Coding Standards

This document defines mandatory coding standards for all TCAI contributors.

---

## 1. Code Structure

### 1.1 Module Size Limits

| Element | Max Lines | Exception |
|---------|-----------|-----------|
| `.py` file | 400 | 500 if justified with comment |
| Class | 200 | Security rule classes exempt |
| Function | 50 | Pipeline orchestrators exempt with comment |

**Exemption comment format**: place a `§1.1 exemption:` line inside the docstring.

```python
def enforce_write(...) -> dict[str, Any]:
    """Run a write-tool operation through the full 6-step security pipeline.

    §1.1 exemption: security pipeline orchestrator — coordinates 6 steps
    spanning scope, deobfuscation, AST rules, circuit breaker, and dispatch.

    Args:
        ...
    """
```

### 1.2 Import Order (enforced by ruff)

1. Standard library
2. Third-party packages
3. Local modules (`from tcai...`)

Each group separated by a blank line. Use `from __future__ import annotations` as the first import.

### 1.3 Package Principles

- Agent layer may import from Gateway layer via public API
- Gateway layer **must not** import from Agent layer (use `knowledge_bridge.py` for needed data)
- Tool modules may import `..common` and stdlib only; never import Gateway core

### 1.4 Module Docstring

Every `.py` file starts with:
```python
"""
Brief one-line summary.

Detailed description (optional, multi-line).
"""
```

---

## 2. Code Formatting (enforced by ruff)

| Rule | Value |
|------|-------|
| Line width | 100 characters |
| Indentation | 4 spaces (no tabs) |
| Quotes | Double `"` |
| Trailing commas | Required in multi-line structures |
| Blank lines | 2 before class, 1 between methods |
| File ending | Exactly one blank line |

### 2.1 Naming Conventions

| Type | Style | Example |
|------|-------|---------|
| Module / file | `snake_case` | `circuit_breaker.py` |
| Class | `PascalCase` | `CircuitBreaker` |
| Public function | `snake_case` | `check_operation()` |
| Private function | `_snake_case` | `_resolve_pid()` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Variable | `snake_case` | `session_id` |
| Boolean variable | `is_` / `has_` / `can_` prefix | `is_sensitive` |

### 2.2 Intra-Module Order

1. Module docstring
2. `from __future__ import annotations`
3. Stdlib imports
4. Third-party imports
5. Local imports
6. Module-level type aliases
7. Module-level constants
8. Classes
9. Functions (public → private)

### 2.3 Toolchain

Linting and formatting are enforced by **ruff**. Configuration lives in `pyproject.toml`
under `[tool.ruff]`. Run before committing:

```powershell
.\tools\python-venv\python.exe -m ruff check src/
.\tools\python-venv\python.exe -m ruff format --check src/
```

Type checking is **recommended** (not yet enforced in CI). Use mypy with the
project's Python venv:

```powershell
.\tools\python-venv\python.exe -m mypy src/ --strict
```

---

## 3. Comments

### 3.1 Language

- **Docstrings**: English (international open-source standard)
- **Inline comments**: English preferred; Chinese allowed for domain-specific notes
- **AI prompts** (`prompts/`): Keep original language

### 3.2 Docstring Format — Google Style

```python
def execute_command(
    cmd: list[str],
    timeout: int = 20,
    *,
    safe_mode: bool = True,
) -> CommandResult:
    """Execute a Windows command with safety guards.

    Args:
        cmd: Command and arguments as a list.
        timeout: Maximum execution time in seconds.
        safe_mode: If True, validate against allowlist first.

    Returns:
        Structured result with stdout, stderr, and success flag.

    Raises:
        SecurityBlockedError: If command not in allowlist.
        ToolExecutionError: If binary not found.
    """
```

### 3.3 Inline Comments

- Explain **why**, not **what** (code says what)
- Required on all security-critical paths
- Mark temporary hacks: `# HACK(username): reason`
- Mark TODOs: `# TODO(username): description`
- Never leave commented-out dead code (use git history)

### 3.4 Type Annotations as Documentation

- All public functions must have complete type annotations
- Use `TypeAlias` for complex types:
  ```python
  type ToolResult = dict[str, Any]
  type SecurityVerdict = Literal["safe", "risky", "blocked"]
  ```

---

## 4. Variables & Data Structures

### 4.1 Forbidden Patterns

- ❌ Module-level mutable globals → use `SessionContext`
- ❌ Mutable default arguments (`def foo(items=[])`)
- ❌ Single-letter variables (except `i`, `j` loop indices, `f` for file objects, `e` for exception objects)
- ❌ Magic numbers/strings inline → use `config.py` or module constant
- ❌ Bare `*args`, `**kwargs` without type annotation

> **Rationale for `f` and `e` exceptions**: `with open(...) as f` and
> `except SomeError as e` are universal Python conventions. Using longer
> names in these two patterns harms readability without adding clarity.

### 4.2 Prefer

- `dataclass` over `dict` for structured data
- `X | None` over empty string/`-1` for missing values
- `Enum` over string constants
- `Sequence[T]` over `list[T]` for read-only parameters
- `Mapping[K, V]` over `dict[K, V]` for read-only parameters
- `frozen=True` on dataclasses by default

---

## 5. Security Coding

### 5.1 Input Validation

- Validate all external input before use (user, LLM output, file content)
- Paths must be normalized + scope-checked
- Command/SQL parameters must use parameterized forms

### 5.2 Command Execution

- Always use `common.run_cmd()` for external commands
- Never `shell=True` with `subprocess`
- Always use list form: `["tasklist", "/fo", "csv"]`

### 5.3 Secrets Management

- API keys via environment variables only
- Never log full API keys
- Sensitive file paths must pass through `dlp.py`

### 5.4 Output Encoding

- All LLM-bound output must pass `injection_filter.py`
- Use stdlib for HTML/JSON encoding (never manual string building)

### 5.5 Dependencies

- Prefer stdlib over third-party
- Run `pip-audit` in CI to scan for vulnerabilities
- This project uses a vendored Python venv (`tools/python-venv/`).
  When adding dependencies, pin exact versions in `pyproject.toml`:
  ```toml
  [project]
  dependencies = ["requests>=2.31,<3", "pyyaml==6.0.1"]
  ```
  Use `>=minimum,<next_major` for libraries; `==exact` for tools whose
  output must be reproducible (e.g. yaml, lxml).

---

## 6. Logging (stdlib `logging` module)

### 6.1 Levels

| Level | Use |
|-------|-----|
| `CRITICAL` | Circuit breaker lock, service unavailable |
| `ERROR` | Tool execution failure, invalid config |
| `WARNING` | Security block (RISKY/BLOCKED verdicts), rate limiting |
| `INFO` | Session start/end, tool invocations, approval decisions |
| `DEBUG` | Deobfuscation stages, AST matching details |

### 6.2 Format

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [module] [session_id] message
```

### 6.3 Output

- Development: stderr
- Production: stderr + `work/tcai.log` (JSONL, rotated at 10MB)

---

## 7. Exception Handling

### 7.1 Hierarchy

```
TCAIError (base)
├── ConfigurationError
├── SecurityBlockedError
├── CircuitBreakerOpenError
├── ToolExecutionError
│   ├── ToolTimeoutError
│   └── ToolNotFoundError
└── ValidationError
```

### 7.2 Rules

- ❌ Never `except Exception: pass`
- ✅ Catch specific exception types
- ✅ If swallowing is truly necessary, log at WARNING with `exc_info=True`
- ✅ Clean up resources with `try/finally` or context managers

### 7.3 Error Propagation

- Gateway layer: exceptions → `{"status": "error", "message": str}`
- Agent layer: exceptions → user-readable message (Chinese, since end users are internet cafe staff)
- Never expose raw tracebacks to end users
- Error messages for operators: concise Chinese, include actionable next step
  ```
  ❌ "KeyError: 'path'"
  ✅ "无法读取注册表路径 HKEY_LOCAL_MACHINE\...，请确认该键值存在"
  ```

---

## 8. Testing (pytest)

### 8.1 Naming

- File: `test_<module>.py`
- Function: `test_<function>_<scenario>_<expected>()`

### 8.2 AAA Pattern

```python
def test_circuit_breaker_rate_limit_triggers():
    # Arrange
    breaker = CircuitBreaker()

    # Act
    for _ in range(6):
        breaker.check("file_write")

    # Assert
    assert breaker.state == "open"
```

### 8.3 Coverage Targets

| Area | Minimum |
|------|---------|
| Security core (ast_rules, deobfuscate, injection_filter, dlp) | 85% |
| Gateway pipeline (gateway, server, router) | 75% |
| Agent layer (loop, learn, mcp_client) | 70% |
| Tool modules | 2 cases each (normal + error) |
| Overall | 75% |

**Enforcement** (target; not yet a CI gate):

```powershell
.\tools\python-venv\python.exe -m pytest tests/ --cov=src/tcai --cov-report=term --cov-fail-under=75
```

CI will adopt `--cov-fail-under` once the test suite reaches the target.
Until then, coverage is informational.

### 8.4 Markers

| Marker | Purpose | CI Trigger |
|--------|---------|------------|
| `@pytest.mark.windows` | Requires Windows | Windows runner only |
| `@pytest.mark.slow` | >2 seconds | PR only |
| `@pytest.mark.integration` | Integration test | Every push |

---

## 9. Git

### 9.1 Commit Format (Conventional Commits)

```
<type>(<scope>): <short description>

<detailed description (optional)>

<related issue (optional)>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `security`
Scopes: `gateway`, `agent`, `tools`, `config`, `tests`, `docs`

### 9.2 Branches

- `main` — stable, CI must pass before merge
- `develop` — integration branch
- `feat/<name>` — feature branches
- `fix/<name>` — bugfix branches

### 9.3 PR Review Checklist

Before requesting review, confirm:

- [ ] `ruff check` and `ruff format` pass
- [ ] All imports in correct order (§1.2)
- [ ] New functions have Google-style docstrings (§3.2) and type annotations (§3.4)
- [ ] No single-letter variables except `i`, `j`, `f`, `e` (§4.1)
- [ ] No magic numbers in new code — use named constants (§4.1)
- [ ] Security-sensitive paths pass through `dlp.py` (§5.3)
- [ ] No `except Exception: pass` (§7.2)
- [ ] New tool modules have at least 2 test cases (§8.3)
- [ ] Commit messages follow Conventional Commits (§9.1)

---

## 10. Documentation

### 10.1 Required Files

- `README.md` — project overview, quick start
- `ARCHITECTURE.md` — full architecture
- `CODING_STANDARDS.md` — this file
- `CONTRIBUTING.md` — how to contribute
- `CHANGELOG.md` — version history
- `CODE_OF_CONDUCT.md` — community standards
- `SECURITY.md` — vulnerability reporting

### 10.2 Language

- Developer-facing: English
- End-user-facing (internet cafe staff): Chinese or bilingual
