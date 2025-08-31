import pdfplumber, re
from datetime import datetime
from .utils import stable_hash

def extract_amount(parts):
    amount_str = parts[-2].replace('$', '').replace(',', '').replace('-', '')
    try:
        amount_value = float(amount_str)
    except ValueError:
        try:
            amount_value = float(parts[-1])
        except ValueError:
            amount_value = 0
    return amount_value

def extract_checking_from_pdf(pdf_path, pattern):
    transactions = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                start_year, end_year = extract_statement_years(text)
                for line in text.split('\n'):
                    match = re.search(pattern, line)
                    if match:
                        parts = line.split()
                        if len(parts) >= 4:
                            trans_date = parts[0]
                            trans_date = convert_trans_date(trans_date, start_year, end_year)
                            reference_number = str(stable_hash(''.join(parts)))
                            amount = extract_amount(parts)
                            description = ' '.join(parts[1:-2])
                            transactions.append({
                                'Transaction Date': trans_date,
                                'Post Date': None,
                                'Reference Number': reference_number,
                                'Description': description,
                                'Amount': amount,
                                'Account Type': 'Checking'
                            })
    except (FileNotFoundError, Exception):
        return None
    return transactions

def extract_credit_from_pdf(pdf_path, pattern):
    transactions = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text();
                if not text: continue
                for line in text.split('\n'):
                    match = re.search(pattern, line)
                    if match:
                        parts = line.split()
                        if len(parts) >= 4:
                            trans_date = datetime.strptime(parts[0], "%m/%d/%y")
                            post_date = datetime.strptime(parts[1], "%m/%d/%y")
                            reference_number = parts[2]
                            amount = parts[-1].replace('$', '')
                            description = ' '.join(parts[3:-1])
                            transactions.append({
                                'Transaction Date': trans_date,
                                'Post Date': post_date,
                                'Reference Number': reference_number,
                                'Description': description,
                                'Amount': amount,
                                'Account Type': 'Credit'
                            })
    except (FileNotFoundError, Exception):
        return None
    return transactions

def extract_statement_years(text):
    statement_period_found = re.search(r'Statement Period', text, re.IGNORECASE)
    statement_period_match = None
    if statement_period_found:
        statement_period_match = re.search(r'(\d{1,2}/\d{1,2}/(\d{2}))\s*-\s*(\d{1,2}/\d{1,2}/(\d{2}))', text)
    start_year = None; end_year = None
    if statement_period_match:
        start_yy = statement_period_match.group(2); end_yy = statement_period_match.group(4)
        start_year = int(start_yy); end_year = int(end_yy)
        start_year = 2000 + start_year if start_year < 50 else 1900 + start_year
        end_year = 2000 + end_year if end_year < 50 else 1900 + end_year
    return start_year, end_year

def convert_trans_date(trans_date, start_year, end_year):
    mm, dd = map(int, trans_date.split('-'))
    year = 0
    if start_year and end_year:
        if start_year == end_year: year = start_year
        elif mm == 12: year = start_year
        elif mm == 1: year = end_year
        else: year = start_year
    trans_date_str = f"{dd:02d}/{mm:02d}/{year:04d}"
    return datetime.strptime(trans_date_str, "%d/%m/%Y")