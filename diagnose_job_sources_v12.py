from __future__ import annotations
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from dotenv import load_dotenv

load_dotenv()

def brave_test():
    key = str(os.getenv("BRAVE_SEARCH_API_KEY", "") or "").strip()
    print("BRAVE_SEARCH_API_KEY:", "OK" if key else "MISSING")
    if not key:
        return
    for label, q in [
        ("TopCV", "ke toan Ha Noi site:topcv.vn"),
        ("Multi", "ke toan Ha Noi (site:topcv.vn OR site:vietnamworks.com OR site:careerviet.vn)"),
    ]:
        params = {
            "q": q,
            "country": "ALL",
            "search_lang": "vi",
            "count": 5,
            "result_filter": "web",
            "operators": "true",
            "spellcheck": "false",
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
            print(f"Brave {label} HTTP: 200")
            print(f"Brave {label} results:", len(results))
            for item in results[:3]:
                print(" -", item.get("title", "")[:110])
                print("   ", item.get("url", "")[:180])
        except HTTPError as e:
            print(f"Brave {label} HTTP:", e.code)
            try:
                print(" error:", e.read().decode("utf-8", "replace")[:700])
            except Exception:
                pass
        except URLError as e:
            print(" network error:", str(e.reason))

def jooble_call(key, keywords, location):
    endpoint = f"https://jooble.org/api/{key}"
    body = json.dumps({
        "keywords": keywords,
        "location": location,
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
        print(f"Jooble [{keywords} | {location}] HTTP: 200")
        print("Jooble jobs:", len(jobs), "/ total:", data.get("totalCount"))
        for item in jobs[:3]:
            print(" -", item.get("title", "")[:110], "|", item.get("location", ""))
        return len(jobs)
    except HTTPError as e:
        print("Jooble HTTP:", e.code)
        return 0
    except URLError as e:
        print("Jooble network error:", str(e.reason))
        return 0

def jooble_test():
    key = str(os.getenv("JOOBLE_API_KEY", "") or "").strip()
    print()
    print("JOOBLE_API_KEY:", "OK" if key else "MISSING")
    if not key:
        return
    n = jooble_call(key, "accountant accounting", "Hanoi")
    if n == 0:
        jooble_call(key, "accountant accounting", "Vietnam")

if __name__ == "__main__":
    brave_test()
    jooble_test()
