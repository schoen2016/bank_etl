from __future__ import annotations
from typing import List, Optional, Dict, Any
import os, re, glob, logging
from .utils import load_config
from .pdf_extract import extract_checking_from_pdf, extract_credit_from_pdf
from .etl import update_sqlite_table

__all__ = [
    "extract_patterns","list_pdf_files","extract_transactions_for_file",
    "extract_all_transactions","move_processed_pdfs","ingest_pdfs"
]

def extract_patterns(config: Dict[str, Any]) -> Dict[str, Optional[str]]:
    dp = config.get('DOC_PATTERNS', {})
    return {
        'credit_pattern': dp.get('CREDIT', {}).get('PATTERN'),
        'checking_pattern': dp.get('CHECKING', {}).get('PATTERN'),
        'credit_file_pattern': dp.get('CREDIT', {}).get('FILENAME_PATTERN'),
        'checking_file_pattern': dp.get('CHECKING', {}).get('FILENAME_PATTERN'),
    }

def list_pdf_files(pdf_dir: str, limit: Optional[int]) -> List[str]:
    paths = glob.glob(os.path.join(pdf_dir, '*.pdf'))
    return paths[:limit] if (limit and limit > 0) else paths

def extract_transactions_for_file(pdf_path: str, patterns: Dict[str, Optional[str]], logger: logging.Logger) -> List[dict]:
    fname = os.path.basename(pdf_path)
    credit_pattern = patterns['credit_pattern']
    checking_pattern = patterns['checking_pattern']
    credit_file_pattern = patterns['credit_file_pattern']
    checking_file_pattern = patterns['checking_file_pattern']
    data = None
    try:
        if credit_file_pattern and re.search(credit_file_pattern, fname):
            if credit_pattern:
                data = extract_credit_from_pdf(pdf_path, credit_pattern)
        elif checking_file_pattern and re.search(checking_file_pattern, fname):
            if checking_pattern:
                data = extract_checking_from_pdf(pdf_path, checking_pattern)
        else:
            if checking_pattern:
                data = extract_checking_from_pdf(pdf_path, checking_pattern)
            if not data and credit_pattern:
                data = extract_credit_from_pdf(pdf_path, credit_pattern)
    except Exception:
        logger.error(f"Failed extracting {fname}")
        return []
    return data or []

def extract_all_transactions(pdf_paths: List[str], patterns: Dict[str, Optional[str]], logger: logging.Logger) -> List[dict]:
    all_tx: List[dict] = []
    for pdf_path in pdf_paths:
        fname = os.path.basename(pdf_path)
        logger.info(f"Processing PDF: {fname}")
        tx = extract_transactions_for_file(pdf_path, patterns, logger)
        if tx:
            logger.info(f"Extracted {len(tx)} transactions from {fname}")
            all_tx.extend(tx)
        else:
            logger.warning(f"No transactions extracted from {fname}")
    return all_tx

def move_processed_pdfs(pdf_paths: List[str], destination: str, logger: logging.Logger) -> None:
    if not destination:
        return
    os.makedirs(destination, exist_ok=True)
    for pdf_path in pdf_paths:
        dest = os.path.join(destination, os.path.basename(pdf_path))
        try:
            os.replace(pdf_path, dest)
            logger.info(f"Moved {pdf_path} -> {dest}")
        except Exception:
            logger.error(f"Failed moving {pdf_path} -> {dest}")

def ingest_pdfs(config_path: str, logger: logging.Logger, move_after: bool = True, limit: Optional[int] = None) -> int:
    config = load_config(config_path)
    db_path = config.get('DB_PATH')
    table_name = config.get('TABLE_NAME')
    pdf_dir = config.get('INGESTION_PATH')
    pdf_storage = config.get('PDF_STORAGE')
    if not all([db_path, table_name, pdf_dir]):
        raise ValueError("Config must include DB_PATH, TABLE_NAME, INGESTION_PATH")
    patterns = extract_patterns(config)
    pdf_paths = list_pdf_files(pdf_dir, limit)
    if not pdf_paths:
        logger.info("No PDF files found to ingest.")
        return 0
    transactions = extract_all_transactions(pdf_paths, patterns, logger)
    if transactions:
        logger.info(f"Upserting {len(transactions)} transactions into {table_name}")
        update_sqlite_table(transactions, db_path=db_path, table_name=table_name)
    else:
        logger.warning("No transactions to load into database.")
    if move_after and pdf_storage:
        move_processed_pdfs(pdf_paths, pdf_storage, logger)
    return len(transactions)
