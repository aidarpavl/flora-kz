"""
ETL: iNaturalist (проект flora-kazahstana) → Supabase.

Запуск:
    export SUPABASE_URL=https://ucrhksetkgmhoxdwwhnh.supabase.co
    export SUPABASE_SERVICE_KEY=<service_role key>
    python etl/load_inat.py                 # полная загрузка / обновление
    python etl/load_inat.py --incremental   # только новые наблюдения
    python etl/load_inat.py --max-pages 5   # быстрый тест (1000 наблюдений)

Шаги: границы областей + природные зоны → таблица areas;
наблюдения → область/зона (point-in-polygon) → observations;
сведения о видах (русские названия, семейства, фото) → taxa.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

INAT = "https://api.inaturalist.org/v1"
PROJECT = os.getenv("INAT_PROJECT", "flora-kazahstana")
ROOT = Path(__file__).resolve().parent.parent
ZONES_FILE = ROOT / "data" / "kz_natural_zones.geojson"
LOCAL_REGIONS_FILE = ROOT / "data" / "kz_regions.geojson"  # необязательный (например, 20 областей 2022 г.)
REGIONS_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/KAZ/ADM1/"
    "geoBoundaries-KAZ-ADM1_simplified.geojson"
)
UA = {"User-Agent": "flora-kz-etl/1.0 (streamlit app; contact via GitHub)"}

# Английские названия geoBoundaries → русские
REGION_RU = [
    ("north kazakhstan", "Северо-Казахстанская область"),
    ("west kazakhstan", "Западно-Казахстанская область"),
    ("east kazakhstan", "Восточно-Казахстанская область"),
    ("akmola", "Акмолинская область"),
    ("aqmola", "Акмолинская область"),
    ("aktobe", "Актюбинская область"),
    ("aqtobe", "Актюбинская область"),
    ("atyrau", "Атырауская область"),
    ("jambyl", "Жамбылская область"),
    ("zhambyl", "Жамбылская область"),
    ("karaganda", "Карагандинская область"),
    ("qaraghandy", "Карагандинская область"),
    ("kostanay", "Костанайская область"),
    ("qostanay", "Костанайская область"),
    ("kyzylorda", "Кызылординская область"),
    ("qyzylorda", "Кызылординская область"),
    ("mangystau", "Мангистауская область"),
    ("mangghystau", "Мангистауская область"),
    ("pavlodar", "Павлодарская область"),
    ("turkistan", "Туркестанская область"),
    ("south kazakhstan", "Туркестанская область"),
    ("abai", "область Абай"),
    ("abay", "область Абай"),
    ("jetisu", "область Жетысу"),
    ("zhetysu", "область Жетысу"),
    ("ulytau", "область Улытау"),
    ("shymkent", "г. Шымкент"),
    ("astana", "г. Астана"),
    ("nur-sultan", "г. Астана"),
    ("baikonur", "г. Байконур"),
    ("almaty region", "Алматинская область"),
    ("almaty oblysy", "Алматинская область"),
    ("almaty city", "г. Алматы"),
    ("almaty", "Алматинская область"),
]


def ru_region(name_en: str) -> str:
    low = name_en.lower()
    if low.strip() in ("almaty", "almaty (city)", "almaty city", "алматы"):
        return "г. Алматы"
    for key, ru in REGION_RU:
        if key in low:
            return ru
    return name_en


# ---------------------------------------------------------------- HTTP

session = requests.Session()
session.headers.update(UA)


def inat_get(path: str, params: dict | None = None, tries: int = 6) -> dict:
    for attempt in range(tries):
        try:
            r = session.get(f"{INAT}{path}", params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            time.sleep(1.0)  # iNat: не более ~1 запроса в секунду
            return r.json()
        except (requests.RequestException, ValueError) as e:
            wait = 5 * (attempt + 1)
            print(f"  ! {e}; повтор через {wait} с", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"iNaturalist недоступен: {path}")


class Supa:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.h = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def upsert(self, table: str, rows: list[dict], on_conflict: str | None = None, batch: int = 500):
        params = {"on_conflict": on_conflict} if on_conflict else None
        headers = {**self.h, "Prefer": "resolution=merge-duplicates,return=minimal"}
        for i in range(0, len(rows), batch):
            chunk = rows[i : i + batch]
            for attempt in range(5):
                r = requests.post(f"{self.base}/{table}", params=params, headers=headers,
                                  data=json.dumps(chunk, ensure_ascii=False), timeout=120)
                if r.status_code < 300:
                    break
                print(f"  ! Supabase {table}: {r.status_code} {r.text[:300]}", file=sys.stderr)
                if r.status_code < 500:
                    raise RuntimeError(r.text)
                time.sleep(5 * (attempt + 1))

    def select_all(self, table: str, select: str, page: int = 1000) -> list[dict]:
        out, offset = [], 0
        while True:
            r = requests.get(f"{self.base}/{table}", headers=self.h,
                             params={"select": select, "limit": page, "offset": offset, "order": "id"},
                             timeout=120)
            r.raise_for_status()
            data = r.json()
            out += data
            if len(data) < page:
                return out
            offset += page

    def max_id(self, table: str) -> int:
        r = requests.get(f"{self.base}/{table}", headers=self.h,
                         params={"select": "id", "order": "id.desc", "limit": 1}, timeout=60)
        r.raise_for_status()
        d = r.json()
        return d[0]["id"] if d else 0


# ---------------------------------------------------------------- Геоданные

def load_regions() -> list[tuple[str, str, object]]:
    if LOCAL_REGIONS_FILE.exists():
        print(f"Области: локальный файл {LOCAL_REGIONS_FILE.name}")
        fc = json.loads(LOCAL_REGIONS_FILE.read_text(encoding="utf-8"))
    else:
        print("Области: загрузка geoBoundaries KAZ ADM1…")
        r = session.get(REGIONS_URL, timeout=120)
        r.raise_for_status()
        fc = r.json()
    regions = []
    for f in fc["features"]:
        p = f.get("properties") or {}
        name_en = p.get("name_en") or p.get("shapeName") or p.get("NAME_1") or p.get("name") or "?"
        name_ru = p.get("name_ru") or ru_region(name_en)
        geom = shape(f["geometry"]).buffer(0)
        regions.append((name_ru, name_en, geom))
    # объединяем полигоны с одинаковым русским названием
    merged: dict[str, tuple[str, object]] = {}
    for ru, en, g in regions:
        if ru in merged:
            merged[ru] = (merged[ru][0], unary_union([merged[ru][1], g]))
        else:
            merged[ru] = (en, g)
    return [(ru, en, g) for ru, (en, g) in merged.items()]


def load_zones(kz_border) -> tuple[list, list]:
    """Возвращает (зоны для классификации, зоны обрезанные по границе для карты)."""
    fc = json.loads(ZONES_FILE.read_text(encoding="utf-8"))
    feats = sorted(fc["features"], key=lambda f: f["properties"].get("priority", 9))
    mountains = unary_union([shape(f["geometry"]) for f in feats if f["properties"]["type"] == "mountain"])
    classify, display = [], []
    for f in feats:
        p = f["properties"]
        g = shape(f["geometry"]).buffer(0)
        classify.append((p["name"], prep(g)))
        clipped = g.intersection(kz_border)
        if p["type"] != "mountain":
            clipped = clipped.difference(mountains)
        if not clipped.is_empty:
            display.append((p["name"], p["name_en"], clipped))
    return classify, display


def geom_json(g, tol: float = 0.01) -> dict:
    gj = mapping(g.simplify(tol, preserve_topology=True))

    def rnd(c):
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            return [round(c[0], 4), round(c[1], 4)]
        return [rnd(x) for x in c]

    return {"type": gj["type"], "coordinates": rnd(gj["coordinates"])}


# ---------------------------------------------------------------- Наблюдения

def species_id(taxon: dict) -> int | None:
    rl = taxon.get("rank_level")
    if rl is None or rl > 10:
        return None
    if rl == 10:
        return taxon["id"]
    if taxon.get("min_species_taxon_id"):
        return taxon["min_species_taxon_id"]
    anc = taxon.get("ancestor_ids") or []
    return anc[-2] if len(anc) >= 2 else None


def parse_obs(o: dict, regions, zones) -> dict | None:
    t = o.get("taxon")
    if not t:
        return None
    sid = species_id(t)
    gj = o.get("geojson") or {}
    coords = gj.get("coordinates")
    if not sid or not coords:
        return None
    lng, lat = float(coords[0]), float(coords[1])
    pt = Point(lng, lat)
    region = next((ru for ru, prepared, _ in regions if prepared.contains(pt)), None)
    if region is None:  # точка на границе/чуть за ней — ближайшая область в пределах ~10 км
        best = min(regions, key=lambda r: r[2].distance(pt))
        if best[2].distance(pt) < 0.1:
            region = best[0]
    zone = next((name for name, prepared in zones if prepared.contains(pt)), None)
    photo = None
    if o.get("photos"):
        photo = (o["photos"][0].get("url") or "").replace("square", "medium") or None
    return {
        "id": o["id"],
        "taxon_id": sid,
        "observed_on": o.get("observed_on"),
        "lat": round(lat, 5),
        "lng": round(lng, 5),
        "quality_grade": o.get("quality_grade"),
        "user_login": None,   # логины авторов не храним — список наблюдателей ведётся только по участникам сайта
        "photo_url": photo,
        "uri": o.get("uri"),
        "region": region,
        "zone": zone,
    }


def fetch_taxa(ids: list[int]) -> list[dict]:
    rows = []
    for i in range(0, len(ids), 30):
        chunk = ids[i : i + 30]
        data = inat_get(f"/taxa/{','.join(map(str, chunk))}", {"locale": "ru"})
        for t in data.get("results", []):
            anc = {a.get("rank"): a.get("name") for a in t.get("ancestors") or []}
            photo = (t.get("default_photo") or {}).get("medium_url")
            rows.append({
                "id": t["id"],
                "name": t.get("name"),
                "rank": t.get("rank"),
                "common_name_ru": t.get("preferred_common_name"),
                "common_name_en": t.get("english_common_name"),
                "family": anc.get("family"),
                "genus": anc.get("genus"),
                "photo_url": photo,
                "wikipedia_url": t.get("wikipedia_url"),
                "inat_url": f"https://www.inaturalist.org/taxa/{t['id']}",
            })
        print(f"  виды: {min(i + 30, len(ids))}/{len(ids)}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incremental", action="store_true", help="только наблюдения новее последнего в БД")
    ap.add_argument("--max-pages", type=int, default=0, help="ограничить число страниц (тест)")
    ap.add_argument("--quality", default="", help="research | needs_id | casual (по умолчанию все)")
    ap.add_argument("--refresh-taxa", action="store_true", help="перезагрузить сведения обо всех видах")
    args = ap.parse_args()

    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("Нужны переменные окружения SUPABASE_URL и SUPABASE_SERVICE_KEY")
    db = Supa(url, key)

    # 1. Территории
    regions_raw = load_regions()
    kz_border = unary_union([g for _, _, g in regions_raw])
    regions = [(ru, prep(g), g) for ru, _, g in regions_raw]
    zones_cls, zones_disp = load_zones(kz_border)
    areas = [{"kind": "region", "name": ru, "name_en": en, "geojson": geom_json(g)} for ru, en, g in regions_raw]
    areas += [{"kind": "zone", "name": n, "name_en": en, "geojson": geom_json(g)} for n, en, g in zones_disp]
    db.upsert("areas", areas, on_conflict="kind,name")
    print(f"Территории: {len(regions_raw)} областей, {len(zones_disp)} зон")

    # 2. Наблюдения
    id_above = db.max_id("observations") if args.incremental else 0
    first = inat_get("/observations", {"project_id": PROJECT, "per_page": 0})
    print(f"В проекте {first.get('total_results')} наблюдений; старт с id > {id_above}")
    seen_species: set[int] = set()
    page, total = 0, 0
    while True:
        params = {"project_id": PROJECT, "per_page": 200, "order_by": "id", "order": "asc",
                  "id_above": id_above}
        if args.quality:
            params["quality_grade"] = args.quality
        res = inat_get("/observations", params).get("results", [])
        if not res:
            break
        rows = [r for r in (parse_obs(o, regions, zones_cls) for o in res) if r]
        db.upsert("observations", rows)
        seen_species.update(r["taxon_id"] for r in rows)
        total += len(rows)
        id_above = res[-1]["id"]
        page += 1
        print(f"  стр. {page}: +{len(rows)} (всего {total}), последний id {id_above}")
        if args.max_pages and page >= args.max_pages:
            break

    # 3. Виды
    have = set() if args.refresh_taxa else {r["id"] for r in db.select_all("taxa", "id")}
    if args.refresh_taxa:
        seen_species |= {r["taxon_id"] for r in db.select_all("observations", "id,taxon_id")}
    need = sorted(seen_species - have)
    print(f"Сведения о видах: нужно загрузить {len(need)}")
    if need:
        db.upsert("taxa", fetch_taxa(need))
    print("Готово ✔")


if __name__ == "__main__":
    main()
