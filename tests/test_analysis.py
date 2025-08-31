from bank_etl.lib import calculate_moving_averages, get_logger

def test_calculate_moving_averages_basic():
    logger = get_logger("analysis_test")
    data = [
        {"transaction_date":"2024-01-05","category":"food","amount":10.0},
        {"transaction_date":"2024-02-10","category":"food","amount":20.0},
        {"transaction_date":"2024-03-15","category":"food","amount":30.0},
    ]
    out = calculate_moving_averages(data, ["food"], logger)

    # should annotate month and rolling averages
    months = [r['month'] for r in out]
    assert months == ["2024-01","2024-02","2024-03"]
    
    # current behavior: 12-month averages are only reported when a full 12-month
    # window is available; with fewer than 12 months the avg is reported as 0.
    last = [r for r in out if r['month']=="2024-03"][0]
    assert last['category_12mo_avg'] == 0
