import hashlib
import logging
import json
from typing import Any, Dict, Optional

def stable_hash(s, length=24):
    if length % 2 != 0 or length > 128 or length <= 0:
        raise ValueError("length must be an even integer between 2 and 128")
    digest_size = length // 2
    h = hashlib.blake2b(s.encode(), digest_size=digest_size)
    return h.hexdigest()[:length]

def safe_float(value, row, logger):
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning(f"Invalid amount: {value} for row: {row}")
        return None

def get_logger(name: str = "py_analysis", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    if not logger.hasHandlers():
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def load_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}")

def parse_month(date_str: str) -> Optional[str]:
    import datetime
    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(date_str, fmt).strftime('%Y-%m')
        except Exception:
            continue
    return None

def month_iter(start, end):
    months = []
    current = start
    while current <= end:
        months.append(current.strftime('%Y-%m'))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months
