import career

def test_source_types():
    assert career._source_info_for_url(
        "https://www.topcv.vn/viec-lam/test"
    ) == ("TopCV", "job_board")
    assert career._source_info_for_url(
        "https://vieclam.gov.vn/test"
    ) == ("Sàn giao dịch việc làm quốc gia", "government")
    assert career._source_info_for_url(
        "https://jobs.lever.co/acme/abc"
    ) == ("Lever", "ats")

def test_company_job_page_detection():
    assert career._looks_like_company_job_page(
        "https://company.vn/careers/engineer",
        "Software Engineer",
        "Join our team in Vietnam",
    )
    assert not career._looks_like_company_job_page(
        "https://example.com/about",
        "About us",
        "Company introduction",
    )

def test_brave_group_query_contains_sites():
    q = career._brave_group_query("kế toán", "Hà Nội", "vn_boards")
    assert "site:topcv.vn" in q
    assert "site:vietnamworks.com" in q

def test_greenhouse_url_parser():
    assert career._greenhouse_parts(
        "https://job-boards.greenhouse.io/acme/jobs/12345"
    ) == ("acme", "12345")

def test_lever_url_parser():
    assert career._lever_parts(
        "https://jobs.lever.co/acme/abc-123"
    ) == ("acme", "abc-123")
