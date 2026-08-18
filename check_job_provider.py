import os
from dotenv import load_dotenv
load_dotenv()
key=str(os.getenv("JOOBLE_API_KEY","") or "").strip()
print("JOOBLE_API_KEY:", "OK" if key else "MISSING")
if not key:
    print("Thêm JOOBLE_API_KEY vào .env rồi restart python app.py")
