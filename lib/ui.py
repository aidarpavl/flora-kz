"""Общие стили и компоненты в духе iNaturalist."""
from __future__ import annotations

import html

import pandas as pd
import pydeck as pdk
import streamlit as st

GREEN = "#74AC00"
KZ_VIEW = pdk.ViewState(latitude=48.0, longitude=67.5, zoom=3.6, pitch=0)
PLACEHOLDER = "https://static.inaturalist.org/images/iconic_taxa/plantae-200px.png"

CSS = f"""
<style>
.block-container {{padding-top: 1.6rem;}}
h1, h2, h3 {{color: #333;}}
.hero {{background: linear-gradient(90deg, {GREEN} 0%, #4f7a00 100%); color: #fff;
        padding: 18px 24px; border-radius: 10px; margin-bottom: 18px;}}
.hero h1 {{color: #fff; margin: 0; font-size: 2rem;}}
.hero p {{margin: 4px 0 0 0; opacity: .9;}}
.stat {{text-align:center; border:1px solid #e5e5e5; border-radius:8px; padding:10px 6px; background:#fff;}}
.stat .n {{font-size: 1.8rem; font-weight: 700; color: {GREEN}; line-height: 1.1;}}
.stat .l {{font-size: .8rem; text-transform: uppercase; color:#777; letter-spacing:.04em;}}
.card {{border:1px solid #e3e3e3; border-radius:8px; overflow:hidden; background:#fff;
        margin-bottom: 6px; height: 100%;}}
.card img {{width:100%; height:150px; object-fit:cover; display:block; background:#f2f2f2;}}
.card .b {{padding:6px 8px 8px 8px;}}
.card .ru {{font-weight:600; font-size:.9rem; color:#333; line-height:1.2; min-height:1.2em;}}
.card .la {{font-style:italic; font-size:.82rem; color:#555;}}
.card .c {{font-size:.78rem; color:{GREEN}; font-weight:600; margin-top:2px;}}
.card a {{text-decoration:none;}}
.muted {{color:#888; font-size:.85rem;}}
</style>
"""


def setup():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = ""):
    st.markdown(f'<div class="hero"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def stats_row(items: list[tuple[str, object]]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        v = f"{value:,}".replace(",", " ") if isinstance(value, int) else (value or "—")
        col.markdown(f'<div class="stat"><div class="n">{v}</div><div class="l">{label}</div></div>',
                     unsafe_allow_html=True)


def species_card(row) -> str:
    ru = html.escape(row.get("common_name_ru") or "")
    la = html.escape(row.get("name") or "")
    img = row.get("photo_url") or PLACEHOLDER
    n = int(row.get("observations") or 0)
    link = row.get("inat_url") or "#"
    return (f'<div class="card"><a href="{link}" target="_blank"><img src="{img}" loading="lazy"></a>'
            f'<div class="b"><div class="ru">{ru or "&nbsp;"}</div><div class="la">{la}</div>'
            f'<div class="c">{n} набл.</div></div></div>')


def territory_picker(key: str, allow_all: bool = True) -> tuple[str, str | None]:
    """Выбор территории: Весь Казахстан / Область / Природная зона."""
    from lib import db

    options = (["Весь Казахстан"] if allow_all else []) + ["Область", "Природная зона"]
    mode = st.radio("Территория", options, horizontal=True, key=f"{key}_mode")
    if mode == "Весь Казахстан":
        return "all", None
    kind = "region" if mode == "Область" else "zone"
    df = db.area_stats(kind)
    if df.empty:
        st.info("Данных по территориям пока нет — запустите ETL.")
        return "all", None
    labels = {r["name"]: f'{r["name"]} — {int(r["species"])} видов' for _, r in df.iterrows()}
    name = st.selectbox("Выберите", list(labels), format_func=labels.get, key=f"{key}_{kind}")
    return kind, name


def color_scale(values: pd.Series):
    """Зелёная шкала для хороплета (светлый → тёмный)."""
    lo, hi = float(values.min() or 0), float(values.max() or 1)
    span = (hi - lo) or 1.0
    out = []
    for v in values:
        t = (float(v) - lo) / span
        out.append([int(230 - 150 * t), int(245 - 85 * t), int(200 - 190 * t), 190])
    return out


def choropleth(kind: str, highlight: str | None = None, points: pd.DataFrame | None = None,
               height: int = 520):
    from lib import db

    shapes = db.areas(kind)
    stats = db.area_stats(kind).set_index("name") if not db.area_stats(kind).empty else pd.DataFrame()
    if not shapes:
        st.info("Геометрии территорий не загружены — запустите ETL.")
        return
    names = [s["name"] for s in shapes]
    species = pd.Series([int(stats.loc[n, "species"]) if n in stats.index else 0 for n in names])
    colors = color_scale(species)
    feats = []
    for s, sp, c in zip(shapes, species, colors):
        obs = int(stats.loc[s["name"], "observations"]) if s["name"] in stats.index else 0
        line = [214, 40, 40, 255] if s["name"] == highlight else [80, 80, 80, 160]
        feats.append({"type": "Feature", "geometry": s["geojson"],
                      "properties": {"name": s["name"], "species": int(sp), "observations": obs,
                                     "fill": c, "line": line,
                                     "lw": 3 if s["name"] == highlight else 1}})
    layers = [pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feats},
                        pickable=True, stroked=True, filled=True,
                        get_fill_color="properties.fill", get_line_color="properties.line",
                        get_line_width="properties.lw", line_width_units="pixels")]
    if points is not None and not points.empty:
        layers.append(point_layer(points))
    tooltip = {"html": "<b>{name}</b><br/>Видов: {species}<br/>Наблюдений: {observations}",
               "style": {"backgroundColor": "#fff", "color": "#333"}}
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=KZ_VIEW, tooltip=tooltip,
                             map_style="light"), height=height)


def point_layer(df: pd.DataFrame):
    return pdk.Layer("ScatterplotLayer", df[["lng", "lat"]].dropna(), get_position="[lng, lat]",
                     get_radius=2500, radius_min_pixels=2, radius_max_pixels=6,
                     get_fill_color=[214, 90, 20, 170], pickable=False)


def footer():
    st.markdown("---")
    st.markdown(
        '<span class="muted">Данные: <a href="https://www.inaturalist.org/projects/flora-kazahstana" '
        'target="_blank">iNaturalist — проект «Флора Казахстана»</a>. Фотографии принадлежат авторам '
        'наблюдений (лицензии CC указаны на iNaturalist). Границы природных зон схематичные.</span>',
        unsafe_allow_html=True)
