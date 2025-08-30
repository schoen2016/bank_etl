"""Transaction categorization utilities.

This module provides functions to assign categories to uncategorized
transactions in the SQLite database using a JSON configuration file
with substring (including wildcard *) patterns per category.
"""
from __future__ import annotations
import sqlite3, json, re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

PatternMap = Dict[str, Sequence[str]]

_wildcard_cache: Dict[str, re.Pattern] = {}

def _compile_pattern(substr: str) -> re.Pattern:
    """Compile a user substring containing * wildcards into a regex.

    Caches compiled patterns for reuse. The match is case-insensitive
    and searches anywhere in the description.
    """
    if substr in _wildcard_cache:
        return _wildcard_cache[substr]
    # Escape then replace escaped wildcard with regex equivalent
    pattern = re.escape(substr).replace(r"\*", ".*")
    compiled = re.compile(pattern, re.IGNORECASE)
    _wildcard_cache[substr] = compiled
    return compiled

def match_substring_with_wildcard(substr: str, description: str) -> bool:
    """Return True if the (possibly wildcard) substring matches description."""
    if not description:
        return False
    return _compile_pattern(substr).search(description) is not None

def choose_category(description: str, category_map: PatternMap) -> str:
    """Return first category whose patterns match description, else 'uncategorized'."""
    desc_lower = description or ""
    for category, patterns in category_map.items():
        for pat in patterns:
            if match_substring_with_wildcard(pat.lower(), desc_lower.lower()):
                return category
    return "uncategorized"

def categorize_transactions(db_path: str, category_map: PatternMap, limit: Optional[int] = None) -> int:
    """Assign categories for uncategorized transactions.

    Args:
        db_path: Path to SQLite database.
        category_map: Mapping of category -> iterable of pattern strings.
        limit: Optional max number of uncategorized transactions to process.
    Returns:
        Count of rows inserted into category table.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
           SELECT t.id, t.description
             FROM transactions t
        LEFT JOIN category c ON t.id = c.transaction_id
            WHERE c.category IS NULL
         ORDER BY t.id ASC
    """)
    rows: List[Tuple[int, str]] = cursor.fetchall()
    processed = 0
    for trans_id, description in rows:
        if limit is not None and processed >= limit:
            break
        cat = choose_category(description or "", category_map)
        cursor.execute("INSERT INTO category (transaction_id, category) VALUES (?, ?)", (trans_id, cat))
        processed += 1
    conn.commit(); conn.close()
    return processed

def load_category_config(path: str) -> PatternMap:
    """Load category JSON file with schema {"categories": {cat: [patterns...]}}"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('categories', {})

__all__ = [
    'match_substring_with_wildcard',
    'choose_category',
    'categorize_transactions',
    'load_category_config',
]
