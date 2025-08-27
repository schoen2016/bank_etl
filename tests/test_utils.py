import datetime
from bank_etl.lib import parse_month, month_iter, safe_float, get_logger

logger = get_logger("test")

def test_parse_month_valid():
    assert parse_month("2024-05-17") == "2024-05"

def test_parse_month_invalid():
    assert parse_month("17/05/2024") is None

def test_month_iter():
    start = datetime.datetime(2024,1,1)
    end = datetime.datetime(2024,3,1)
    assert month_iter(start,end) == ["2024-01","2024-02","2024-03"]

def test_safe_float():
    assert safe_float("12.5", {}, logger) == 12.5
    assert safe_float("bad", {"amount":"bad"}, logger) is None
