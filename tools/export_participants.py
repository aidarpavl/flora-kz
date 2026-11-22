"""Выгрузка участников сайта (наблюдатели и эксперты) в репозиторий: data/site/participants.json и .csv.

Запускается GitHub Actions (.github/workflows/participants.yml) каждый час; коммит — только если что-то изменилось.
Выгружаются только открытые данные (как на страницах сайта): логин, имя, дата регистрации,
число наблюдений, видов и определений. E-mail и пароли не выгружаются.
"""
import csv
import json
import os
import sys
import urllib.request

URL = (os.getenv("SUPABASE_URL") or "https://ucrhksetkgmhoxdwwhnh.supabase.co").rstrip("/")
KEY = os.getenv("SUPABASE_KEY") or ""
if not KEY:
    sys.exit("Нет ключа Supabase: добавьте секрет SUPABASE_SERVICE_KEY (или SUPABASE_ANON_KEY) в Settings → Secrets → Actions")

headers = {"apikey": KEY, "Content-Type": "application/json"}
if not KEY.startswith("sb_"):
    headers["Authorization"] = f"Bearer {KEY}"
req = urllib.request.Request(f"{URL}/rest/v1/rpc/api_participants_export", data=b"{}", headers=headers, method="POST")
rows = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())

os.makedirs("data/site", exist_ok=True)
with open("data/site/participants.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
cols = ["login", "name", "registered", "observations", "species", "identifications"]
with open("data/site/participants.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c) for c in cols})
print("participants:", len(rows))
