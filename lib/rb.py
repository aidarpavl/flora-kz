"""Общие помощники раздела «Красная книга» (каталог и страница вида)."""
from __future__ import annotations

import base64
import io

import folium
import streamlit as st

from lib import db, ui
from lib.i18n import lang

CATS = {
    "I": ("I — исчезающие", "I — жойылып бара жатқан", "#d62728"),
    "II": ("II — редкие", "II — сирек", "#ff7f0e"),
    "III": ("III — сокращающиеся", "III — азайып бара жатқан", "#e6b800"),
    "IV": ("IV — неопределённые", "IV — анықталмаған", "#7f7f7f"),
    "V": ("V — восстанавливаемые", "V — қалпына келтірілетін", "#2ca02c"),
}


def kk() -> bool:
    return lang() == "kk"


def cat_label(c):
    return CATS[c][1 if kk() else 0] if c in CATS else "—"


def cat_color(c):
    return CATS.get(c, ("", "", "#555"))[2]


def nm(r):
    """Название на текущем языке."""
    return (r.get("name_kk") or r.get("name_ru") or r.get("latin")) if kk() else (r.get("name_ru") or r.get("latin"))


def txt(r, base):
    """Текст поля на текущем языке (с запасным вариантом на другом)."""
    a, b = (f"{base}_kk", f"{base}_ru") if kk() else (f"{base}_ru", f"{base}_kk")
    return r.get(a) or r.get(b) or ""


def photo_uri(sid):
    p = db.safe("api_rb_photo", {}, p_id=int(sid)) or {}
    return f"data:{p.get('mime') or 'image/jpeg'};base64,{p['data']}" if p.get("data") else None


def card_img(r):
    """Фото: загруженное пользователем, иначе из iNaturalist/Википедии/GBIF, иначе заглушка."""
    if r.get("has_photo"):
        return photo_uri(r["id"]) or ui.PLACEHOLDER
    return r.get("photo_url") or ui.PLACEHOLDER


def fam(r):
    """Семейство на текущем языке + латынь."""
    loc = (r.get("family_kk") or r.get("family_ru")) if kk() else r.get("family_ru")
    lat = r.get("family")
    return f"{loc} ({lat})" if loc and lat else (loc or lat or "—")


def kingdom() -> str:
    """Какой раздел открыт: растения ('plantae') или животные ('animalia'). Ставится в app.py по адресу страницы."""
    return st.session_state.get("rb_kingdom", "plantae")


def animal() -> bool:
    return kingdom() == "animalia"


def L(ru, kz):
    return kz if kk() else ru


def title() -> str:
    if animal():
        return L("Краснокнижные животные Казахстана", "Қазақстанның Қызыл кітабына енген жануарлар")
    from lib.i18n import t
    return t("rb_title")


def icon() -> str:
    return "🐾" if animal() else "🌺"


def list_url() -> str:
    return f"./{'redbook_animals' if animal() else 'redbook'}?lang={lang()}"


def page_link(sid) -> str:
    return f"./{'rb_animal' if animal() else 'rb_species'}?id={int(sid)}&lang={lang()}"


def tax_lines(r) -> str:
    """Тип / класс / отряд (для животных) — строки markdown."""
    out = []
    for lab_ru, lab_kk, base, lat in (("Тип", "Тип", "phylum", "phylum"), ("Класс", "Класс", "class", "class_lat"),
                                      ("Отряд", "Отряд", "order", "order_lat")):
        loc = r.get(f"{base}_kk" if kk() else f"{base}_ru") or r.get(f"{base}_ru")
        la = r.get(lat)
        if loc or la:
            out.append(f"**{L(lab_ru, lab_kk)}:** {loc or ''}{f' ({la})' if la and loc else (la or '')}")
    return "  \n".join(out)


def to_b64(upload):
    if not upload:
        return None, None
    try:
        from PIL import Image
        img = Image.open(upload).convert("RGB")
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
    except Exception:
        return base64.b64encode(upload.getvalue()).decode(), upload.type


def add_layers(m, data_points, data_ranges):
    for g in data_ranges:
        c = cat_color(g.get("category"))
        folium.GeoJson(g["geojson"], style_function=lambda f, c=c: {"color": c, "weight": 2, "fillColor": c,
                                                                      "fillOpacity": 0.25},
                       tooltip=f"{nm(g)} · {g.get('latin')}").add_to(m)
    if len(data_points) > 400:          # много точек — быстрые кластеры
        from folium.plugins import FastMarkerCluster
        cb = """function (row) {
          var m = L.circleMarker(new L.LatLng(row[0], row[1]), {radius: 6, color: '#fff', weight: 1,
                                 fillColor: row[3], fillOpacity: 0.95});
          m.bindTooltip(row[2]); return m; }"""
        FastMarkerCluster([[p["lat"], p["lng"], p.get("title") or "", cat_color(p.get("category"))] for p in data_points],
                          callback=cb, options={"maxClusterRadius": 40, "disableClusteringAtZoom": 9}).add_to(m)
        return
    for p in data_points:
        c = cat_color(p.get("category"))
        folium.CircleMarker([p["lat"], p["lng"]], radius=7, color="#fff", weight=2, fill=True, fill_color=c,
                            fill_opacity=0.95, tooltip=p.get("title")).add_to(m)
