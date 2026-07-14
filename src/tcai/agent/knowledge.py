"""
TCAI Agent — structured in-memory knowledge base.

Parses Markdown + YAML frontmatter files into structured dict indexes.
No FTS5, no SQLite — pure Python dict for speed, safety, and
zero syntax-injection surface.

Indexes: game, category, error_code, tags, and keyword-based content lookup.
Search is O(1) dict lookups + set intersections — no query language parsing,
so user input like ``**3**`` or ``11:58`` can never crash the search.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


class KnowledgeBase:
    """Structured in-memory knowledge base with dict indexes.

    Indexes are rebuilt from scratch on every startup.
    Knowledge files are external .md with YAML frontmatter
    (game, category, error_code, tags).

    Args:
        knowledge_path: Directory containing .md knowledge files.
            Falls back to config.knowledge_path if None.
    """

    def __init__(self, knowledge_path: Path | str | None = None) -> None:
        from ..gateway.config import config  # Late import to avoid circular

        raw = knowledge_path or config.knowledge_path
        self._knowledge_path = Path(raw) if isinstance(raw, str) else raw

        # Entry storage (list of dicts)
        self._entries: list[dict[str, Any]] = []

        # Structured indexes: field value -> set of entry indices
        self._by_game: dict[str, set[int]] = {}
        self._by_category: dict[str, set[int]] = {}
        self._by_code: dict[str, set[int]] = {}
        self._by_tags: dict[str, set[int]] = {}

        # Content-level keyword index
        self._keyword_index: dict[str, set[int]] = {}

        self._load_all()

    # ── Index building ──

    def _load_all(self) -> None:
        """Load all .md files and populate indexes."""
        if not self._knowledge_path or not self._knowledge_path.exists():
            return

        for md_file in sorted(self._knowledge_path.rglob("*.md")):
            try:
                parsed = self._parse_md(md_file)
                if parsed["content"]:
                    self._index_entry(parsed)
            except (UnicodeDecodeError, OSError):
                continue

    @staticmethod
    def _parse_md(filepath: Path) -> dict[str, Any]:
        """Parse a Markdown file with YAML frontmatter.

        Supported frontmatter fields:
            title, game, category, error_code, tags

        Returns:
            Dict with title, game, category, error_code (list),
            tags (list), and content string.
        """
        text = filepath.read_text(encoding="utf-8")

        frontmatter: dict = {}
        content = text

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if fm_match:
            try:
                frontmatter = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                import logging
                logging.getLogger(__name__).warning(
                    f"YAML parse failed in {filepath}", exc_info=True,
                )
            content = text[fm_match.end():]

        # Normalize error_code to list
        raw_code = frontmatter.get("error_code", "")
        if isinstance(raw_code, str):
            codes = [
                code.strip() for code in raw_code.replace("，", ",").split(",")
                if code.strip()
            ]
        elif isinstance(raw_code, list):
            codes = [str(code).strip() for code in raw_code if code]
        else:
            codes = []

        # Normalize tags to list
        raw_tags = frontmatter.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [
                tag.strip() for tag in raw_tags.replace("，", ",").split(",")
                if tag.strip()
            ]
        elif isinstance(raw_tags, list):
            tags = [tag.strip() for tag in raw_tags if tag]
        else:
            tags = []

        return {
            "title": str(frontmatter.get("title", filepath.stem)),
            "game": str(frontmatter.get("game", "")),
            "category": str(frontmatter.get("category", "")),
            "error_code": codes,
            "tags": tags,
            "content": content.strip(),
        }

    def _index_entry(self, entry: dict[str, Any]) -> None:
        """Add a single entry to all indexes."""
        idx = len(self._entries)
        self._entries.append(entry)

        if entry["game"]:
            self._by_game.setdefault(entry["game"], set()).add(idx)

        if entry["category"]:
            self._by_category.setdefault(entry["category"], set()).add(idx)

        for code in entry["error_code"]:
            self._by_code.setdefault(code, set()).add(idx)

        for tag in entry["tags"]:
            self._by_tags.setdefault(tag, set()).add(idx)

        # Index content: extract meaningful words from first 500 chars
        content_words = set(
            word for word in re.findall(r"[\w\u4e00-\u9fff]+", entry["content"][:500])
            if len(word) > 1
        )
        for word in content_words:
            self._keyword_index.setdefault(word, set()).add(idx)

    # ── Search ──

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the knowledge base using structured indexes.

        Tokenizes the query and scores each entry by how many tokens
        match across all indexes.  No FTS5 query language is involved,
        so special characters (``*`` ``:`` ``"`` etc.) can never cause
        syntax errors.

        Args:
            query: Free-text search query.
            limit: Maximum results to return.

        Returns:
            List of result dicts with title, game, category, tags,
            snippet, and score keys.
        """
        if not query.strip():
            return []

        # Tokenize query into meaningful words
        tokens = [
            token for token in re.findall(r"[\w\u4e00-\u9fff]+", query)
            if len(token) > 1
        ]
        if not tokens:
            return []

        # Score each entry by how many tokens match across all indexes
        scores: dict[int, int] = {}
        for token in tokens:
            candidates: set[int] = set()
            if token in self._by_game:
                candidates.update(self._by_game[token])
            if token in self._by_category:
                candidates.update(self._by_category[token])
            if token in self._by_code:
                candidates.update(self._by_code[token])
            if token in self._by_tags:
                candidates.update(self._by_tags[token])
            if token in self._keyword_index:
                candidates.update(self._keyword_index[token])

            for idx in candidates:
                scores[idx] = scores.get(idx, 0) + 1

        # Sort by score descending, return top N
        ranked = sorted(scores.items(), key=lambda x: -x[1])

        results: list[dict[str, Any]] = []
        for idx, score in ranked[:limit]:
            entry = self._entries[idx]
            content = entry["content"]
            snippet = content[:200] + "..." if len(content) > 200 else content
            results.append({
                "title": entry["title"],
                "game": entry["game"],
                "category": entry["category"],
                "tags": entry["tags"],
                "snippet": snippet,
                "score": score,
            })

        return results

    @property
    def count(self) -> int:
        """Number of loaded knowledge entries."""
        return len(self._entries)

    @property
    def is_loaded(self) -> bool:
        """Whether any knowledge entries have been loaded."""
        return len(self._entries) > 0

