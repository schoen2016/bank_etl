import sqlite3, tempfile, os, json
from bank_etl import categorize

CATEGORY_JSON = {
    "categories": {
        "GROCERIES": ["SAFEWAY", "TRADER*JOES"],
        "COFFEE": ["STARBUCKS"],
    }
}

def setup_db(db_path):
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, transaction_date TEXT, description TEXT, amount REAL, reference_number TEXT, account_type TEXT)")
    cur.execute("CREATE TABLE category (transaction_id INTEGER, category TEXT)")
    cur.executemany("INSERT INTO transactions (transaction_date, description, amount, reference_number, account_type) VALUES (?,?,?,?,?)", [
        ("2024-01-01", "SAFEWAY STORE 123", 10.0, "ref1", "checking"),
        ("2024-01-02", "STARBUCKS #456", 5.0, "ref2", "checking"),
        ("2024-01-03", "Random Merchant", 7.0, "ref3", "checking"),
    ])
    conn.commit(); conn.close()

def test_categorize_transactions():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, 'test.db')
        setup_db(db_path)
        processed = categorize.categorize_transactions(db_path, CATEGORY_JSON['categories'])
        assert processed == 3
        conn = sqlite3.connect(db_path); cur = conn.cursor()
        cur.execute("SELECT t.description, c.category FROM transactions t JOIN category c ON t.id=c.transaction_id ORDER BY t.id")
        rows = cur.fetchall(); conn.close()
        assert rows[0][1] == 'GROCERIES'
        assert rows[1][1] == 'COFFEE'
    # Unknown remains the literal 'uncategorized'
    assert rows[2][1] == 'uncategorized'

