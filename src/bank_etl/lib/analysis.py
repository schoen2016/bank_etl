import logging
from typing import List, Dict, Any, Iterable
from collections import defaultdict
import json
import datetime
from .utils import safe_float, parse_month, month_iter

def _normalize_categories(categories: Iterable[str]) -> List[str]:
    return [c.lower() for c in categories]

def _extract_months(data: List[Dict[str, Any]]) -> List[str]:
    return [m for m in (parse_month(r.get('transaction_date')) for r in data if r.get('transaction_date')) if m]

def _determine_month_range(months: List[str]) -> List[str]:
    if not months:
        return []
    earliest = min(months)
    latest = max(months)
    first_day_earliest = datetime.datetime.strptime(earliest, '%Y-%m').replace(day=1)
    first_day_latest = datetime.datetime.strptime(latest, '%Y-%m').replace(day=1)
    return month_iter(first_day_earliest, first_day_latest)

def _aggregate_monthly_totals(data: List[Dict[str, Any]], categories_lower: List[str], month_range: List[str], logger: logging.Logger):
    monthly_totals = defaultdict(lambda: defaultdict(float))
    for month in month_range:
        month_rows = [row for row in data if parse_month(row.get('transaction_date')) == month]
        for category_lower in categories_lower:
            total = 0.0
            count = 0
            for row in month_rows:
                amount = safe_float(row.get('amount', 0), row, logger)
                row_category = str(row.get('category')).lower()
                if amount is not None and row_category == category_lower:
                    total += amount
                    count += 1
            monthly_totals[month][category_lower] = {'total': total, 'count': count}
    return monthly_totals

def _compute_category_avgs(monthly_totals, categories_lower: List[str]) -> Dict[str, Dict[str, float]]:
    months_sorted = sorted(monthly_totals.keys())
    category_avgs: Dict[str, Dict[str, float]] = defaultdict(dict)
    for cat in categories_lower:
        for i, month in enumerate(months_sorted):
            window = months_sorted[max(0, i - 11): i + 1]
            total = sum(monthly_totals[m].get(cat, {}).get('total', 0) for m in window)
            category_avgs[cat][month] = total / len(window) if window else 0.0
    return category_avgs

def _compute_group_avgs(monthly_totals, categories_lower: List[str]) -> Dict[str, float]:
    months_sorted = sorted(monthly_totals.keys())
    group_avgs: Dict[str, float] = {}
    for i, month in enumerate(months_sorted):
        window = months_sorted[max(0, i - 11): i + 1]
        total = sum(sum(monthly_totals[m].get(cat, {}).get('total', 0) for cat in categories_lower) for m in window)
        group_avgs[month] = total / len(window) if window else 0.0
    return group_avgs

def _annotate_rows(data: List[Dict[str, Any]], monthly_totals, category_avgs, group_avgs) -> None:
    for row in data:
        date_str = row.get('transaction_date')
        category = row.get('category')
        category_lower = str(category).lower() if category else None
        month = parse_month(date_str)
        row['month'] = month
        row['category_12mo_avg'] = category_avgs.get(category_lower, {}).get(month, 0) if month and category_lower else 0
        row['group_12mo_avg'] = group_avgs.get(month, 0) if month else 0
        cat_month_info = monthly_totals.get(month, {}).get(category_lower, {}) if month else {}
        row['category_12mo_count'] = cat_month_info.get('count', 0) if month and category_lower else 0
        group_month_info = monthly_totals.get(month, {}) if month else {}
        row['group_12mo_count'] = sum(info.get('count', 0) for info in group_month_info.values()) if month else 0

def calculate_moving_averages(data: List[Dict[str, Any]], categories: List[str], logger: logging.Logger) -> List[Dict[str, Any]]:
    if not data:
        logger.warning("No data provided for analysis.")
        return []
    categories_lower = _normalize_categories(categories)
    months_list = _extract_months(data)
    month_range = _determine_month_range(months_list)
    monthly_totals = _aggregate_monthly_totals(data, categories_lower, month_range, logger)
    category_avgs = _compute_category_avgs(monthly_totals, categories_lower)
    group_avgs = _compute_group_avgs(monthly_totals, categories_lower)
    _annotate_rows(data, monthly_totals, category_avgs, group_avgs)
    return data
