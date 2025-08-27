DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transaction_date DATE,
  post_date DATE,
  reference_number TEXT,
  description TEXT,
  amount REAL,
  account_type TEXT,
  hash TEXT,
  update_datetime TEXT DEFAULT (datetime('now'))
);