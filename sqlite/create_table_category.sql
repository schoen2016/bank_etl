DROP TABLE IF EXISTS category;
CREATE TABLE category (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transaction_id INTEGER,
  category TEXT,
  FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);