import career

def test_jooble_alias_accounting():
    assert "accountant" in career._jooble_keyword_query("Kế toán").lower()

def test_unknown_role_preserved():
    assert career._jooble_keyword_query("Quantum Accountant") == "Quantum Accountant"

def test_brave_query_keeps_hanoi():
    q = career._brave_group_query("Kế toán", "Hà Nội", "core_job_boards")
    assert "Hà Nội" in q
    assert "site:topcv.vn" in q
