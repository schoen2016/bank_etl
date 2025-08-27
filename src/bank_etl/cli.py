"""CLI adapter (src layout)."""
from __future__ import annotations

import argparse
from .lib.utils import get_logger
from .lib.ingest import ingest_pdfs


def main(argv=None) -> int:  # pragma: no cover - thin wrapper
    parser = argparse.ArgumentParser(prog="bank-etl")
    parser.add_argument("--mode", choices=["ingest"], default="ingest")
    parser.add_argument("--config", default="config_db.json")
    parser.add_argument("--no-move", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--log-file")
    args = parser.parse_args(argv)
    logger = get_logger("bank_etl", log_file=args.log_file)
    if args.mode == "ingest":
        count = ingest_pdfs(args.config, logger, move_after=not args.no_move, limit=args.limit)
        logger.info(f"Ingested {count} transactions")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())