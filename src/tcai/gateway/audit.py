"""
TCAI Gateway — JSONL audit logging.

Every security decision is logged as a JSONL entry (append-only).
Audit logs can be queried by date range and verdict.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import re

from .paths import AUDIT_LOG
from . import logging_setup

logger = logging_setup.get_logger(__name__)

# China Standard Time
TZ_CN = timezone(timedelta(hours=8))


def log_decision(
    *,
    session_id: str,
    tool: str,
    params: dict[str, Any],
    verdict: str,
    reason: str = "",
    level: str = "",
    approval_id: str = "",
    sub_agent_warning: str = "",
    exit_code: int = 0,
    snapshot_path: str = "",
) -> None:
    """Record a security decision to the audit log.

    This is the single entry point for all security decisions.
    Called by the gateway pipeline after each tool operation.

    Args:
        session_id: Session identifier.
        tool: Tool name.
        params: Tool parameters (will be sanitized before logging).
        verdict: Security verdict (safe/risky/blocked/pending_approval).
        reason: Human-readable reason for the verdict.
        level: AST level.
        approval_id: Approval ID if applicable.
        sub_agent_warning: Sub-agent instigation warning if detected.
        exit_code: Tool exit code (0 = success).
        snapshot_path: Path to pre-operation snapshot if created.
    """
    entry = {
        "session_id": session_id,
        "timestamp": datetime.now(TZ_CN).isoformat(),
        "tool": tool,
        "params": _sanitize_params(params),
        "verdict": verdict,
        "reason": reason,
        "level": level,
        "approval_id": approval_id,
        "sub_agent_warning": sub_agent_warning,
        "exit_code": exit_code,
        "snapshot_path": snapshot_path,
    }

    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"Failed to write audit log: {e}")


def read_logs(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    verdict: str | None = None,
    max_entries: int = 100,
) -> list[dict[str, Any]]:
    """Query audit logs with optional filters.

    Args:
        since: Return entries after this datetime (inclusive).
        until: Return entries before this datetime (inclusive).
        verdict: Filter by verdict (safe/risky/blocked).
        max_entries: Maximum entries to return.

    Returns:
        List of audit entries.
    """
    if not AUDIT_LOG.exists():
        return []

    results: list[dict[str, Any]] = []

    try:
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                if len(results) >= max_entries:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Apply filters
                try:
                    ts = datetime.fromisoformat(entry.get("timestamp", ""))
                except (ValueError, TypeError):
                    continue  # Skip entries with missing or malformed timestamps
                if since and ts < since:
                    continue
                if until and ts > until:
                    continue
                if verdict and entry.get("verdict") != verdict:
                    continue

                results.append(entry)
    except OSError as e:
        logger.error(f"Failed to read audit log: {e}")

    return results


def get_stats() -> dict[str, int]:
    """Get audit log statistics (counts by verdict).

    Returns:
        Dict with counts for each verdict type and total.
    """
    stats: dict[str, int] = {"total": 0}
    if not AUDIT_LOG.exists():
        return stats

    try:
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                verdict = entry.get("verdict", "unknown")
                stats[verdict] = stats.get(verdict, 0) + 1
                stats["total"] += 1
    except OSError:
        logger.warning("Audit stats read failed", exc_info=True)

    return stats




# Patterns for value-level sensitive data detection
_SENSITIVE_VALUE_RE: re.Pattern[str] = re.compile(
    r"(Bearer\s+[A-Za-z0-9._\-]{20,}|"
    r"sk-[A-Za-z0-9]{20,}|"
    r"[A-Za-z0-9+/=]{40,})",
)


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Sanitize sensitive fields from params before logging.

    Redacts: password, token, secret, key, credential, apikey.
    Truncates: string values longer than 200 characters.
    """
    safe: dict[str, Any] = {}
    sensitive_keys = {"password", "token", "secret", "key", "credential", "apikey"}

    for k, v in params.items():
        if any(s in k.lower() for s in sensitive_keys):
            safe[k] = "***"
        elif isinstance(v, str) and len(v) > 200:
            safe[k] = v[:197] + "..."
        elif isinstance(v, str) and _SENSITIVE_VALUE_RE.search(v):
            safe[k] = "***"
        else:
            safe[k] = v

    return safe

