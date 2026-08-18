import career

def test_brave_queries_stay_under_documented_limits():
    for group in career.BRAVE_SOURCE_GROUPS:
        q = career._brave_group_query("Kế toán", "Hà Nội", group)
        assert len(q) <= 360
        assert len(q.split()) <= 45

def test_core_query_contains_major_vietnam_sources():
    q = career._brave_group_query("Kế toán", "Hà Nội", "core_job_boards")
    assert "site:topcv.vn" in q
    assert "site:vietnamworks.com" in q
    assert "site:careerviet.vn" in q

def test_company_public_query_is_broad():
    q = career._brave_group_query("Kế toán", "Hà Nội", "company_public")
    assert "tuyển dụng" in q
    assert "site:" not in q
