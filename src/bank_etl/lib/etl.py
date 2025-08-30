import sqlite3, csv, logging, os
from typing import List, Dict, Any, Optional

def update_sqlite_table(data, db_path, table_name):
    if not data:
        print("No data to update in SQLite.")
        return
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for row in data:
        cursor.execute(f'''SELECT 1 FROM {table_name} WHERE [reference_number]=?''', (row.get('Reference Number'),))
        result = cursor.fetchone()
        if result:
            try:
                cursor.execute(f'''UPDATE {table_name} SET [transaction_date]=?, [post_date]=?, [description]=?, [amount]=? WHERE [reference_number]=?''', (
                  row.get('Transaction Date'), row.get('Post Date'), row.get('Description'), float(str(row.get('Amount', 0)).replace(',', '')), row.get('Reference Number')
                ))
            except Exception as e:
                print(f"Error updating row with Reference Number {row.get('Reference Number')}: {e}")
                print(f"Row data: {row}")
                continue
        else:
            cursor.execute(f'''INSERT INTO {table_name} ([transaction_date], [post_date], [reference_number], [description], [amount], [account_type]) VALUES (?, ?, ?, ?, ?, ?)''', (
                row.get('Transaction Date'), row.get('Post Date'), row.get('Reference Number'), row.get('Description'), float(str(row.get('Amount', 0)).replace(',', '')), row.get('Account Type', 'Unknown' if 'Account Type' not in row else row.get('Account Type', 'Unknown'))
            ))
    conn.commit(); conn.close(); print(f"Table '{table_name}' updated in SQLite database at {db_path}")

def get_group_categories(config: Dict[str, Any], group_name: str) -> List[str]:
    if 'groups' in config and group_name in config['groups']:
        return config['groups'][group_name]
    if group_name in config:
        return config[group_name]
    return []

def fetch_group_data(db_path: str, categories: List[str], logger: logging.Logger) -> List[Dict[str, Any]]:
    # Defensive normalization: callers may pass a dict (config), a single string,
    # or any iterable of category names. Convert to a list of strings for
    # building positional parameters for SQLite.
    if not categories:
        logger.warning("No categories found for group.")
        return []

    # Accept dict (category->patterns), str (single category), or iterable
    if isinstance(categories, dict):
        categories = list(categories.keys())
    elif isinstance(categories, str):
        categories = [categories]
    else:
        try:
            categories = list(categories)
        except Exception:
            logger.error("Invalid categories type passed to fetch_group_data")
            return []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(categories))
        query = (
            "SELECT t.id as transaction_id, t.transaction_date, t.description, t.amount, c.category "
            "FROM transactions t LEFT JOIN category c ON t.id = c.transaction_id "
            f"WHERE c.category IN ({placeholders}) "
            "AND t.id IN ( SELECT max(id) FROM transactions as t GROUP BY t.transaction_date, t.description, t.amount )"
        )
        params = tuple(categories)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        col_names = [d[0] for d in cursor.description]
        data = [dict(zip(col_names, row)) for row in rows]
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return []

def write_csv(data: List[Any], output_path: str, logger: logging.Logger, headers: Optional[List[str]] = None):
    if not data:
        logger.warning("No data to write to CSV."); return
    if headers is None:
        if isinstance(data[0], dict): headers = list(data[0].keys())
        elif isinstance(data[0], (list, tuple)): headers = [f"col{i+1}" for i in range(len(data[0]))]
        else: raise ValueError("Cannot infer headers from data structure.")
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f) if not isinstance(data[0], dict) else csv.DictWriter(f, fieldnames=headers)
            writer.writeheader() if hasattr(writer, 'writeheader') else writer.writerow(headers)
            for row in data:
                if isinstance(row, dict): writer.writerow(row)
                else: writer.writerow(row)
        logger.info(f"CSV written to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}"); raise
