from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

for name in ("JOOBLE_API_KEY", "BRAVE_SEARCH_API_KEY"):
    value = str(os.getenv(name, "") or "").strip()
    print(f"{name}:", "OK" if value else "MISSING")

print()
print("Coverage:")
print("- Jooble structured feed")
print("- Vietnam job boards via Brave")
print("- National employment / DOLAB")
print("- Manpower / Adecco / RGF")
print("- Lever / Greenhouse / Ashby / SmartRecruiters discovery")
print("- Company career pages")
print("- Public LinkedIn/Facebook/Threads pages when indexed")
