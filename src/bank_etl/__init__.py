"""bank_etl top-level package (src layout).

This package re-exports commonly used submodules from `bank_etl.lib`
so callers can import `bank_etl.utils` instead of `bank_etl.lib.utils`.
"""

import bank_etl.lib as lib  # keep lib available

# Module re-exports (still available as bank_etl.utils, etc.)
from bank_etl.lib import utils as utils  # noqa: E402
from bank_etl.lib import etl as etl  # noqa: E402
from bank_etl.lib import ingest as ingest  # noqa: E402
from bank_etl.lib import analysis as analysis  # noqa: E402
from bank_etl.lib import pdf_extract as pdf_extract  # noqa: E402
try:
	from bank_etl.lib import categorize as categorize  # noqa: E402
except Exception:
	categorize = None

# Explicit function-level re-exports so callers can do:
#   from bank_etl import ingest_pdfs, calculate_moving_averages, ...
# (We avoid wildcard star imports to keep namespace clean of helper modules.)

# utils
# utils
from bank_etl.lib.utils import stable_hash, safe_float, get_logger, load_config, parse_month, month_iter  # noqa: E402
# etl
# etl
from bank_etl.lib.etl import update_sqlite_table, get_group_categories, fetch_group_data, write_csv  # noqa: E402
# ingest
# ingest
from bank_etl.lib.ingest import (
	ingest_pdfs,
	extract_patterns,
	list_pdf_files,
	extract_transactions_for_file,
	extract_all_transactions,
	move_processed_pdfs,
)  # noqa: E402
# analysis
# analysis
from bank_etl.lib.analysis import calculate_moving_averages  # noqa: E402
# pdf_extract
# pdf_extract
from bank_etl.lib.pdf_extract import (
	extract_checking_from_pdf,
	extract_credit_from_pdf,
	extract_statement_years,
	convert_trans_date,
	extract_amount,
)  # noqa: E402
# categorize helpers: optional import so `import bank_etl` works even when
# the installed distribution lacks the categorize module (e.g. older wheel).
try:
	from bank_etl.lib.categorize import (
		match_substring_with_wildcard,
		choose_category,
		categorize_transactions,
		load_category_config,
	)  # noqa: E402
except Exception:
	match_substring_with_wildcard = None
	choose_category = None
	categorize_transactions = None
	load_category_config = None

__all__ = [
	# modules
	"lib",
	"utils",
	"etl",
	"ingest",
	"analysis",
	"pdf_extract",
	"categorize",
	# utils funcs
	"stable_hash",
	"safe_float",
	"get_logger",
	"load_config",
	"parse_month",
	"month_iter",
	# etl funcs
	"update_sqlite_table",
	"get_group_categories",
	"fetch_group_data",
	"write_csv",
	# ingest funcs
	"ingest_pdfs",
	"extract_patterns",
	"list_pdf_files",
	"extract_transactions_for_file",
	"extract_all_transactions",
	"move_processed_pdfs",
	# analysis
	"calculate_moving_averages",
	# pdf extract
	"extract_checking_from_pdf",
	"extract_credit_from_pdf",
	"extract_statement_years",
	"convert_trans_date",
	"extract_amount",
	# categorize
	"match_substring_with_wildcard",
	"choose_category",
	"categorize_transactions",
	"load_category_config",
]

__version__ = "0.1.1"