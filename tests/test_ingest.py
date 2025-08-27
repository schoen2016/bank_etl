from bank_etl.lib import extract_patterns

def test_extract_patterns():
    cfg = {"DOC_PATTERNS": {"CREDIT":{"PATTERN":"C","FILENAME_PATTERN":"CR"},"CHECKING":{"PATTERN":"K","FILENAME_PATTERN":"CK"}}}
    pats = extract_patterns(cfg)
    assert pats['credit_pattern']=="C"
    assert pats['checking_pattern']=="K"
    assert pats['credit_file_pattern']=="CR"
    assert pats['checking_file_pattern']=="CK"