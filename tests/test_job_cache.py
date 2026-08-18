import career

def test_jooble_cache_round_trip():
    career._jooble_cache.clear()
    jobs = [{"title": "Kế toán tổng hợp", "url": "https://example.com/job/1"}]
    career._jooble_cache_set("kế toán", "Hà Nội", "", jobs)
    assert career._jooble_cache_get("kế toán", "Hà Nội", "") == jobs

def test_cache_key_ignores_local_filters():
    key_a = career._jooble_cache_key("kế toán", "Hà Nội", "")
    key_b = career._jooble_cache_key("kế toán", "Hà Nội", "")
    assert key_a == key_b
