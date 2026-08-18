from __future__ import annotations
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from dotenv import load_dotenv

load_dotenv()

def test_brave():
    key = str(os.getenv("BRAVE_SEARCH_API_KEY", "") or "").strip()
    print("BRAVE_SEARCH_API_KEY:", "OK" if key else "MISSING")
    if not key:
        return
    params = {
        "q": "ke toan Ha Noi site:topcv.vn",
        "country": "VN",
        "search_lang": "vi",
        "count": 5,
        "result_filter": "web",
        "operators": "true",
    }
    url = "https://api.search.brave.com/res/v1/web/search?" + urlencode(params)
    req = Request(url, headers={
        "Accept": "application/json",
        "X-Subscription-Token": key,
        "User-Agent": "Mozilla/5.0 Chrome/151.0",
    })
    try:
        with urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        results = ((data.get("web") or {}).get("results") or [])
        print("Brave HTTP: 200")
        print("Brave web results:", len(results))
        for item in results[:3]:
            print(" -", item.get("title", "")[:100])
            print("   ", item.get("url", "")[:180])
    except HTTPError as e:
        print("Brave HTTP:", e.code)
        try:
            print("Brave error:", e.read().decode("utf-8", "replace")[:500])
        except Exception:
            pass
    except URLError as e:
        print("Brave network error:", str(e.reason))

def test_jooble():
    key = str(os.getenv("JOOBLE_API_KEY", "") or "").strip()
    print()
    print("JOOBLE_API_KEY:", "OK" if key else "MISSING")
    if not key:
        return
    endpoint = f"https://jooble.org/api/{key}"
    body = json.dumps({
        "keywords": "kế toán",
        "location": "Hà Nội",
        "page": "1",
        "ResultOnPage": "5",
        "companysearch": "false",
    }).encode("utf-8")
    req = Request(endpoint, data=body, method="POST", headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "MoLoi diagnostic",
    })
    try:
        with urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        jobs = data.get("jobs") or []
        print("Jooble HTTP: 200")
        print("Jooble jobs:", len(jobs), "/ total:", data.get("totalCount"))
        for item in jobs[:3]:
            print(" -", item.get("title", "")[:100], "|", item.get("location", ""))
    except HTTPError as e:
        print("Jooble HTTP:", e.code)
        try:
            print("Jooble error:", e.read().decode("utf-8", "replace")[:500])
        except Exception:
            pass
    except URLError as e:
        print("Jooble network error:", str(e.reason))

if __name__ == "__main__":
    test_brave()
    test_jooble()
