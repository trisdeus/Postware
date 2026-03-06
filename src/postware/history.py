"""
History manager module for Postware.

This module handles all history.json I/O operations including:
- Atomic read/write with corruption recovery
- Record pruning to maintain exactly 30 records
- Query methods for promotional ratio, pillars, deduplication

All functions in this module import ONLY from models.py to maintain
the dependency layering rule.
"""

import json
import logging
import os
import shutil
from datetime import date, timedelta
from pathlib import Path

from postware.models import GenerationRecord, HistoryError, HistoryWriteError


# =============================================================================
# CONSTANTS
# =============================================================================

MAX_HISTORY_RECORDS: int = 30
"""Maximum number of records retained in history.json."""

logger = logging.getLogger("postware")


# =============================================================================
# PUBLIC API
# =============================================================================


def load(path: Path) -> list[GenerationRecord]:
    """
    Load generation records from history.json file.

    Reads and parses the history.json file at the given path. Handles missing
    files gracefully by returning an empty list, and recovers from corruption
    by backing up the corrupt file to a .bak file.

    Args:
        path: Path to the history.json file.

    Returns:
        List of GenerationRecord objects. Returns empty list if file doesn't
        exist or is corrupt.

    Raises:
        HistoryError: If an unexpected error occurs during file reading.
    """
    if not path.exists():
        logger.info("history.json not found, starting fresh")
        return []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        records = [GenerationRecord.model_validate(record) for record in data]
        return records

    except json.JSONDecodeError as e:
        backup_path = path.with_suffix(".bak")
        try:
            shutil.copy2(path, backup_path)
            logger.warning(
                f"history.json is corrupt, backed up to {backup_path.name} "
                "and starting fresh"
            )
        except OSError as backup_error:
            logger.warning(
                f"history.json is corrupt and could not be backed up: "
                f"{backup_error}. Starting fresh"
            )
        return []

    except OSError as e:
        raise HistoryError(f"Failed to read history.json: {e}") from e


def save(records: list[GenerationRecord], path: Path) -> None:
    """
    Save generation records to history.json with atomic write and pruning.

    Prunes records to exactly MAX_HISTORY_RECORDS (30) before saving, keeping
    the most recent records. Uses atomic write pattern: writes to a temporary
    file first, then atomically replaces the original file.

    Args:
        records: List of GenerationRecord objects to save.
        path: Path to the history.json file.

    Raises:
        HistoryWriteError: If the write operation fails.
    """
    # Prune to exactly MAX_HISTORY_RECORDS, keeping most recent
    pruned_records = _prune_records(records, MAX_HISTORY_RECORDS)

    # Prepare data for serialization
    data = [record.model_dump(mode="json") for record in pruned_records]

    # Atomic write: write to temp file first, then replace
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        os.replace(tmp_path, path)

    except OSError as e:
        # Clean up temp file if it exists
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

        raise HistoryWriteError(f"Failed to write history.json: {e}") from e


def get_promo_ratio(
    records: list[GenerationRecord], window_days: int = 14
) -> float:
    """
    Calculate the promotional ratio within the specified time window.

    Counts records where is_promotional=True within the last window_days
    and divides by the total number of records in that window.

    Args:
        records: List of GenerationRecord objects to analyze.
        window_days: Number of days to look back (default 14).

    Returns:
        Promotional ratio as a float between 0.0 and 1.0. Returns 0.0 if
        there are no records in the window.
    """
    if not records:
        return 0.0

    cutoff_date = date.today() - timedelta(days=window_days)

    # Filter records within the window
    window_records = [
        r for r in records if date.fromisoformat(r.date) >= cutoff_date
    ]

    if not window_records:
        return 0.0

    promo_count = sum(1 for r in window_records if r.is_promotional)
    return promo_count / len(window_records)


def get_recent_pillars(records: list[GenerationRecord], n: int = 7) -> list[str]:
    """
    Get pillar names from the most recent n records.

    Returns a list of pillar names ordered from most recent to oldest.

    Args:
        records: List of GenerationRecord objects to analyze.
        n: Number of recent records to consider (default 7).

    Returns:
        List of pillar names (strings) from the most recent n records.
        Returns empty list if there are no records.
    """
    if not records:
        return []

    # Sort by date descending (most recent first) and take n
    sorted_records = sorted(
        records, key=lambda r: date.fromisoformat(r.date), reverse=True
    )
    recent_records = sorted_records[:n]

    return [r.pillar.value for r in recent_records]


def get_today_record(records: list[GenerationRecord]) -> GenerationRecord | None:
    """
    Find the record for today's date.

    Searches through the records to find one where the date matches today's
    date in ISO format (YYYY-MM-DD).

    Args:
        records: List of GenerationRecord objects to search.

    Returns:
        The GenerationRecord for today, or None if not found.
    """
    if not records:
        return None

    today_str = date.today().isoformat()

    for record in records:
        if record.date == today_str:
            return record

    return None


def get_deduplication_context(
    records: list[GenerationRecord], n: int = 10
) -> list[str]:
    """
    Get topic/context strings from recent n records for deduplication.

    Extracts the primary topic or context from each record to help the
    generation engine avoid repeating recent topics.

    Args:
        records: List of GenerationRecord objects to analyze.
        n: Number of recent records to consider (default 10).

    Returns:
        List of topic/context strings from recent records. Returns empty
        list if there are no records.
    """
    if not records:
        return []

    # Sort by date descending (most recent first) and take n
    sorted_records = sorted(
        records, key=lambda r: date.fromisoformat(r.date), reverse=True
    )
    recent_records = sorted_records[:n]

    # Extract context from each record - using the pillar and date as context
    context = []
    for record in recent_records:
        # Create a context string from pillar and a short date
        context.append(f"{record.pillar.value}:{record.date}")

    return context


# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _prune_records(
    records: list[GenerationRecord], max_records: int
) -> list[GenerationRecord]:
    """
    Prune records to the specified maximum, keeping most recent.

    Args:
        records: List of GenerationRecord objects to prune.
        max_records: Maximum number of records to keep.

    Returns:
        Pruned list of records, keeping the most recent ones.
    """
    if len(records) <= max_records:
        return records

    # Sort by date descending (most recent first)
    sorted_records = sorted(
        records, key=lambda r: date.fromisoformat(r.date), reverse=True
    )

    # Keep only the most recent max_records
    return sorted_records[:max_records]
