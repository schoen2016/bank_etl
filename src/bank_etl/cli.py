"""CLI adapter (src layout).

Provides a single console entrypoint for ingestion and analysis modes.
"""
from __future__ import annotations

import argparse
import os
from typing import List, Optional

from bank_etl.lib.utils import get_logger
from bank_etl.lib import load_config
from bank_etl.lib import ingest_pdfs
from bank_etl.lib import get_group_categories
from bank_etl.lib import fetch_group_data
from bank_etl.lib import write_csv
from bank_etl.lib import calculate_moving_averages
from bank_etl.lib import categorize_transactions


def run_analysis(
    db_config_path: str,
    category_config_path: str,
    groups: Optional[List[str]],
    logger,
    output_dir: str,
    headers: Optional[List[str]] = None,
) -> int:
    """Run 12-month moving average analysis for category groups.

    This function mirrors the behavior used by the dev runner: it loads the DB
    and category configs, optionally categorizes uncategorized transactions,
    then computes and writes per-group CSVs with rolling averages.
    """
    db_config = load_config(db_config_path)
    category_config = load_config(category_config_path)
    db_path = db_config.get("DB_PATH")
    if not db_path:
        raise ValueError("DB_PATH not found in db config")

    # Categorize uncategorized transactions first
    category_map = category_config.get("categories", {})
    if category_map:
        assigned = categorize_transactions(db_path, category_map)
        logger.info(f"Categorization step inserted {assigned} category rows.")
    else:
        logger.warning("No 'categories' map found in category config; skipping categorization step.")

    # Auto-discover groups if none explicitly provided
    if not groups or len(groups) == 0:
        if "groups" in category_config and isinstance(category_config["groups"], dict):
            groups = list(category_config["groups"].keys())
        else:
            groups = [k for k in category_config.keys() if not k.startswith("_")]

    os.makedirs(output_dir, exist_ok=True)
    processed = 0
    for group in groups:
        logger.info(f"Analyzing group: {group}")
        categories = get_group_categories(category_config, group)
        if not categories:
            logger.warning(f"No categories for group '{group}', skipping")
            continue

        data = fetch_group_data(db_path, categories, logger)
        if not data:
            logger.warning(f"No data returned for group '{group}', skipping")
            continue

        data = calculate_moving_averages(data, categories, logger)

        _out_headers = None
        if headers:
            _out_headers = list(headers)
            for field in [
                "category_12mo_avg",
                "group_12mo_avg",
                "category_12mo_count",
                "group_12mo_count",
                "month",
            ]:
                if field not in _out_headers:
                    _out_headers.append(field)

        output_path = os.path.join(output_dir, f"analysis_{group}.csv")
        write_csv(data, output_path, logger, headers=_out_headers)
        processed += 1
    return processed


def main(argv=None) -> int:  # pragma: no cover - thin wrapper for console script
    parser = argparse.ArgumentParser(prog="bank-etl")
    parser.add_argument("--mode", choices=["ingest", "analyze", "both"], default="both")
    parser.add_argument("--config", default="config_db.json")
    parser.add_argument("--no-move", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--category-config", help="Path to category config (required for analyze modes)")
    parser.add_argument("--group", action="append", dest="groups", help="Category group name (use multiple --group for more)")
    parser.add_argument("--output-dir", default='.', help='Directory for analysis CSV outputs (default: current)')
    parser.add_argument("--headers", nargs='+', help='Optional custom CSV headers (analysis)')
    parser.add_argument("--log-file")
    args = parser.parse_args(argv)

    logger = get_logger("bank_pipeline", log_file=args.log_file)
    try:
        if args.mode in ("ingest", "both"):
            ingested = ingest_pdfs(args.config, logger, move_after=not args.no_move, limit=args.limit)
            logger.info(f"Ingestion complete. {ingested} transactions processed.")

        if args.mode in ("analyze", "both"):
            if not args.category_config:
                raise ValueError("--category-config is required for analysis modes")
            processed_groups = run_analysis(
                db_config_path=args.config,
                category_config_path=args.category_config,
                groups=args.groups,
                logger=logger,
                output_dir=args.output_dir,
                headers=args.headers,
            )
            logger.info(f"Analysis complete. {processed_groups} group(s) processed.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())