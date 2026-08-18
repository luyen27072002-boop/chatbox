from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "dataset_source"}
SKIP_NAMES = {"app.db"}
TEXT_SUFFIXES = {".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg"}
PATTERNS = [
    ("OpenAI-style secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Generic bearer/JWT-like secret", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{30,}\b", re.I)),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]


def tracked_env_files() -> list[str]:
    try:
        output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    return [line for line in output.splitlines() if Path(line).name == ".env" or line.endswith(".env")]


def main() -> int:
    problems: list[str] = []
    envs = tracked_env_files()
    if envs:
        problems.append("Tracked .env file(s): " + ", ".join(envs))

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path.name == ".env" or (path.suffix.lower() not in TEXT_SUFFIXES and not path.name.startswith(".env.example")):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for label, pattern in PATTERNS:
            if pattern.search(text):
                problems.append(f"{label}: {path.relative_to(ROOT)}")

    if problems:
        print("SECURITY SCAN FAILED")
        for item in problems:
            print(" -", item)
        return 1
    print("SECURITY SCAN PASS: no tracked .env and no obvious hard-coded secret patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
