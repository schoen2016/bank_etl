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
    # Precompute sorted months so we can check window lengths per month
    months_sorted = sorted(monthly_totals.keys())
    for row in data:
        date_str = row.get('transaction_date')
        category = row.get('category')
        category_lower = str(category).lower() if category else None
        month = parse_month(date_str)
        row['month'] = month

        # Default counts and avgs
        row['category_12mo_avg'] = 0
        row['group_12mo_avg'] = 0
        row['category_12mo_count'] = 0
        row['group_12mo_count'] = 0

        if not month:
            continue

        # Determine if a full 12-month window exists for this month
        try:
            idx = months_sorted.index(month)
        except ValueError:
            # month not in monthly_totals, leave defaults
            continue

        window = months_sorted[max(0, idx - 11): idx + 1]
        full_window = len(window) >= 12

        # counts
        cat_month_info = monthly_totals.get(month, {}).get(category_lower, {}) if category_lower else {}
        row['category_12mo_count'] = cat_month_info.get('count', 0)
        group_month_info = monthly_totals.get(month, {})
        row['group_12mo_count'] = sum(info.get('count', 0) for info in group_month_info.values())

        # Only set averages if we have a full 12-month window
        if full_window and category_lower:
            row['category_12mo_avg'] = category_avgs.get(category_lower, {}).get(month, 0)
        if full_window:
            row['group_12mo_avg'] = group_avgs.get(month, 0)

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

def calculate_monthly_categories(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return monthly totals per category as a list of dictionaries.

    Each item in the returned list corresponds to a month string (YYYY-MM)
    and contains the total amount for each category observed in `data`.

    Example return value:
      [
        { 'month': '2024-01', 'groceries': 123.45, 'utilities': 67.00 },
        { 'month': '2024-02', 'groceries': 98.00,  'utilities': 80.00 },
      ]

    The function normalizes category names to lowercase.
    """
    logger = logging.getLogger(__name__)
    if not data:
        logger.debug("calculate_monthly_categories: no data provided")
        return []

    # discover categories present in the data and normalize
    raw_cats = sorted({row.get('category') for row in data if row.get('category')})
    categories_lower = _normalize_categories([str(c) for c in raw_cats])
    if not categories_lower:
        logger.debug("calculate_monthly_categories: no categories found in data")
        return []

    # determine the full month range and aggregate totals
    month_range = _determine_month_range(_extract_months(data))
    if not month_range:
        logger.debug("calculate_monthly_categories: no month range could be determined")
        return []

    monthly_totals = _aggregate_monthly_totals(data, categories_lower, month_range, logger)

    # Compute 12-month moving averages (per-category and group)
    category_avgs = _compute_category_avgs(monthly_totals, categories_lower)
    group_avgs = _compute_group_avgs(monthly_totals, categories_lower)

    # Build list of dicts, one per month, with totals per category, month_total,
    # and 12-month moving average fields.
    results: List[Dict[str, Any]] = []
    for month in month_range:
        row: Dict[str, Any] = {"month": month}
        month_info = monthly_totals.get(month, {})
        month_sum = 0.0
        for cat in categories_lower:
            val = month_info.get(cat, {}).get('total', 0.0)
            row[cat] = val
            month_sum += val
            # per-category 12mo average, key: <category>_12mo_avg
            avg_key = f"{cat}_12mo_avg"
            row[avg_key] = category_avgs.get(cat, {}).get(month, 0.0)

        # include a summation/total for the month across all categories
        row['month_total'] = month_sum
        # group 12-month moving average
        row['group_12mo_avg'] = group_avgs.get(month, 0.0)
        results.append(row)

    return results

