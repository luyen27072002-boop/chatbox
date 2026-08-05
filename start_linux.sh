#!/usr/bin/env sh
set -eu
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python app.py
