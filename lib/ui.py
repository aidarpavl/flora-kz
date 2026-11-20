"""Общие компоненты в стиле страницы проекта iNaturalist."""
from __future__ import annotations

import html
import math
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import streamlit as st

from lib import db

GREEN = "#74AC00"
INAT = "https://www.inaturalist.org"
PROJECT_URL = f"{INAT}/projects/flora-kazahstana"
PLACEHOLDER = "https://static.inaturalist.org/images/iconic_taxa/plantae-200px.png"
USER_PLACEHOLDER = "https://static.inaturalist.org/attachment_defaults/users/icons/defaults/thumb.png"
KZ_VIEW = pdk.ViewState(latitude=48.0, longitude=67.5, zoom=3.7, pitch=0)
QUALITY = {"research": "Исследовательский", "needs_id": "Требуется идентификация", "casual": "Обыкновенное"}
RANKS = {"genus": "Род", "family": "Семейство", "subfamily": "Подсемейство", "tribe": "Триба",
         "order": "Порядок", "class": "Класс", "kingdom": "Царство", "section": "Секция",
         "subgenus": "Подрод", "hybrid": "Гибрид", "complex": "Комплекс"}

CSS = f"""
<style>
.block-container {{padding-top: 1rem; max-width: 1250px;}}
.banner {{display:flex; border-radius:4px; overflow:hidden; margin-bottom:14px; min-height:170px;}}
.banner .l {{flex:2; background:{GREEN} repeating-radial-gradient(circle at 30% 40%, rgba(255,255,255,.08) 0 2px, transparent 2px 22px);
             position:relative;}}
.banner .l .t {{position:absolute; left:22px; bottom:20px; background:#333; color:#fff; font-size:1.6rem;
               padding:6px 14px;}}
.banner .r {{flex:1; background:#689c00; color:#fff; padding:16px 20px; font-size:.9rem;}}
.banner .r h3 {{color:#fff; margin:0 0 6px 0; font-size:1.25rem;}}
.banner .r a {{color:#fff;}}
.counters {{display:flex; gap:34px; align-items:flex-end; border-bottom:1px solid #ddd; padding:2px 4px 6px; margin-bottom:14px; flex-wrap:wrap;}}
.counters .c .n {{font-size:1.55rem; color:#555; line-height:1.1;}}
.counters .c .l {{font-size:.78rem; color:#777; text-transform:uppercase; letter-spacing:.03em;}}
.counters .scope {{margin-left:auto; color:{GREEN}; font-weight:600; font-size:.9rem;}}
.grid {{display:grid; grid-template-columns:repeat(auto-fill, minmax(170px, 1fr)); gap:14px;}}
.card {{background:#fff; border:1px solid #e3e3e3; border-radius:3px; overflow:hidden; box-shadow:0 1px 2px rgba(0,0,0,.06);}}
.card a {{text-decoration:none; color:inherit;}}
.card .ph {{position:relative; height:150px; background:#eee center/cover no-repeat;}}
.card .badge {{position:absolute; left:0; bottom:0; right:0; padding:3px 6px; color:#fff; font-size:.75rem;
              background:linear-gradient(transparent, rgba(0,0,0,.65));}}
.card .b {{padding:6px 8px 9px;}}
.card .cn {{font-size:.9rem; color:#333; line-height:1.2; min-height:1.1em; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;}}
.card .sn {{font-size:.8rem; color:#555; font-style:italic; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;}}
.obs {{background:#444; border-radius:3px; overflow:hidden;}}
.obs .ph {{height:170px; background:#555 center/cover no-repeat; position:relative;}}
.obs .av {{position:absolute; right:8px; bottom:-18px; width:40px; height:40px; border-radius:50%; border:2px solid #fff;
          background:#ccc center/cover no-repeat;}}
.obs .b {{padding:8px 10px 8px; color:#fff; min-height:72px;}}
.obs .cn {{font-size:.92rem; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;}}
.obs .sn {{font-size:.78rem; opacity:.9; font-style:italic; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;}}
.obs .m {{font-size:.75rem; opacity:.85; text-align:right; margin-top:4px;}}
.board {{background:#fff; border:1px solid #e3e3e3; padding:14px 16px;}}
.board h4 {{margin:0 0 8px 0; font-weight:400; font-size:1.2rem;}}
.board .row {{display:flex; align-items:center; gap:10px; border-bottom:1px solid #eee; padding:6px 0; font-size:.9rem;}}
.board .row img {{width:30px; height:30px; border-radius:50%; object-fit:cover;}}
.board .row img.sq {{border-radius:2px;}}
.board .row .v {{margin-left:auto; color:#333;}}
.board .row a {{color:#333; text-decoration:none;}}
.muted {{color:#888; font-size:.85rem;}}
.q-research {{color:{GREEN};}} .q-needs_id {{color:#c9a400;}} .q-casual {{color:#999;}}
</style>
"""


# ---------- форматирование ----------

def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def esc(s) -> str:
    return html.escape(str(s)) if s is not None and not (isinstance(s, float) and math.isnan(s)) else ""


def ago(ts) -> str:
    if not ts:
        return ""
    try:
        t = pd.to_datetime(ts, utc=True).to_pydatetime()
    except Exception:
        return ""
    d = (datetime.now(timezone.utc) - t).days
    if d < 1:
        return "сегодня"
    if d < 30:
        return f"{d} дн"
    if d < 365:
        return f"{d // 30}мес"
    return f"{d // 365}г"


def taxon_title(row) -> tuple[str, str]:
    """(общее название, научное с рангом) для наблюдения."""
    common = row.get("obs_common_name") or ""
    sci = row.get("obs_taxon_name") or "Неизвестно"
    rank = row.get("obs_taxon_rank") or ""
    sci_full = f"{RANKS[rank]} {sci}" if rank in RANKS else sci
    return (common or sci_full), (sci_full if common else "")


# ---------- территория (глобальный фильтр) ----------

def scope() -> tuple[str, str]:
    if "scope" not in st.session_state:
        qp = st.query_params.get("scope", "all:all")
        kind, _, name = qp.partition(":")
        st.session_state.scope = (kind or "all", name or "all")
    return st.session_state.scope


def scope_label(kind, name) -> str:
    return "Весь Казахстан" if kind == "all" else name


def sidebar_scope():
    kind, name = scope()
    with st.sidebar:
        st.markdown("### 🗺️ Территория")
        options = ["Весь Казахстан", "Область", "Природная зона"]
        idx = {"all": 0, "region": 1, "zone": 2}.get(kind, 0)
        mode = st.radio("Показывать данные", options, index=idx, label_visibility="collapsed")
        if mode == "Весь Казахстан":
            new = ("all", "all")
        else:
            k = "region" if mode == "Область" else "zone"
            items = db.areas(k)
            names = [a["name"] for a in items]
            if not names:
                st.info("Территории ещё не загружены.")
                new = ("all", "all")
            else:
                labels = {a["name"]: f'{a["name"]} · {fmt(a["species"])} видов' for a in items}
                cur = name if (kind == k and name in names) else names[0]
                sel = st.selectbox(mode, names, index=names.index(cur), format_func=labels.get)
                new = (k, sel)
        if new != st.session_state.scope:
            st.session_state.scope = new
            st.query_params["scope"] = f"{new[0]}:{new[1]}"
            st.rerun()
        st.caption("Фильтр применяется ко всем вкладкам.")
        p = db.progress()
        if p:
            st.markdown("---")
            st.caption(f"В базе: {fmt(p.get('observations'))} наблюдений, {fmt(p.get('taxa'))} видов. "
                       "Статистика обновляется каждые 10 минут.")
        st.markdown(f"[Проект на iNaturalist ↗]({PROJECT_URL})")


# ---------- шапка ----------

def setup():
    st.markdown(CSS, unsafe_allow_html=True)


def header():
    kind, name = scope()
    s = db.stats(kind, name)
    st.markdown(
        f"""<div class="banner"><div class="l"><div class="t">Флора Казахстана</div></div>
        <div class="r"><h3>Подробнее</h3>Народный проект по изучению диких растений Казахстана.
        Наблюдения из проекта iNaturalist с разбивкой по областям и природным зонам.<br><br>
        <a href="{PROJECT_URL}" target="_blank">Открыть проект на iNaturalist ›</a></div></div>
        <div class="counters">
          <div class="c"><div class="n">{fmt(s.get('observations'))}</div><div class="l">наблюдений</div></div>
          <div class="c"><div class="n">{fmt(s.get('species'))}</div><div class="l">видов</div></div>
          <div class="c"><div class="n">{fmt(s.get('identifiers'))}</div><div class="l">экспертов</div></div>
          <div class="c"><div class="n">{fmt(s.get('observers'))}</div><div class="l">наблюдателей</div></div>
          <div class="scope">📍 {esc(scope_label(kind, name))}</div>
        </div>""", unsafe_allow_html=True)
    return s


# ---------- карточки ----------

def taxon_link(taxon_id) -> str:
    kind, name = scope()
    return f"./taxon?id={taxon_id}&scope={quote(kind + ':' + name)}"


def species_cards(df: pd.DataFrame):
    if df.empty:
        st.info("Видов не найдено.")
        return
    parts = []
    for _, r in df.iterrows():
        img = r.get("photo_url") or PLACEHOLDER
        cn = esc(r.get("common_name_ru") or r.get("common_name_en") or r.get("name"))
        sn = esc(r.get("name"))
        parts.append(
            f'<div class="card"><a href="{taxon_link(r["taxon_id"])}" target="_self">'
            f'<div class="ph" style="background-image:url(\'{esc(img)}\')">'
            f'<div class="badge">{fmt(r.get("n"))} наблюдений</div></div>'
            f'<div class="b"><div class="cn">{cn}</div><div class="sn">{sn}</div></div></a></div>')
    st.markdown(f'<div class="grid">{"".join(parts)}</div>', unsafe_allow_html=True)


def observation_cards(df: pd.DataFrame):
    if df.empty:
        st.info("Наблюдений не найдено.")
        return
    parts = []
    for _, r in df.iterrows():
        cn, sn = taxon_title(r)
        img = r.get("photo_url") or PLACEHOLDER
        av = r.get("user_icon") or USER_PLACEHOLDER
        meta = f'🛡 {fmt(r.get("identifications_count") or 0)} · {ago(r.get("created_at") or r.get("observed_on"))}'
        parts.append(
            f'<div class="obs"><a href="{esc(r.get("uri"))}" target="_blank" style="text-decoration:none;color:inherit">'
            f'<div class="ph" style="background-image:url(\'{esc(img)}\')">'
            f'<div class="av" style="background-image:url(\'{esc(av)}\')" title="{esc(r.get("user_login"))}"></div></div>'
            f'<div class="b"><div class="cn">{esc(cn)}</div><div class="sn">{esc(sn)}</div>'
            f'<div class="m">{meta}</div></div></a></div>')
    st.markdown(f'<div class="grid">{"".join(parts)}</div>', unsafe_allow_html=True)


def board(title: str, rows: list[tuple[str, str, str, str]], square=False):
    """rows: (картинка, подпись, ссылка, значение)."""
    items = "".join(
        f'<div class="row"><img class="{"sq" if square else ""}" src="{esc(img) or USER_PLACEHOLDER}">'
        f'<a href="{esc(link)}" target="{"_self" if link.startswith("./") else "_blank"}">{esc(label)}</a>'
        f'<span class="v">{esc(val)}</span></div>'
        for img, label, link, val in rows)
    st.markdown(f'<div class="board"><h4>{esc(title)}</h4>{items or "<span class=muted>Нет данных</span>"}</div>',
                unsafe_allow_html=True)


# ---------- карты ----------

def _cells_layer(cells: pd.DataFrame):
    return pdk.Layer("HeatmapLayer", cells, get_position="[lng, lat]", get_weight="n",
                     radius_pixels=28, intensity=1.2, threshold=0.03, aggregation="SUM",
                     color_range=[[255, 237, 160], [254, 217, 118], [254, 178, 76],
                                  [253, 141, 60], [240, 59, 32], [189, 0, 38]])


def _grid_layer(cells: pd.DataFrame):
    df = cells.copy()
    if df.empty:
        return None
    lg = df["n"].clip(lower=1).map(math.log10)
    mx = max(float(lg.max()), 1.0)
    df["c"] = [[255, int(200 - 170 * v / mx), int(80 - 70 * v / mx), 200] for v in lg]
    df["x"] = df["lng"] - 0.025
    df["y"] = df["lat"] - 0.025
    return pdk.Layer("GridCellLayer", df, get_position="[x, y]", cell_size=5000,
                     extruded=False, get_fill_color="c", pickable=True)


def _points_layer(pts: pd.DataFrame):
    df = pts.copy()
    df["color"] = df["quality"].map({"research": [116, 172, 0, 220], "needs_id": [235, 190, 0, 220]}) \
        .apply(lambda c: c if isinstance(c, list) else [150, 150, 150, 200])
    return pdk.Layer("ScatterplotLayer", df, id="points", get_position="[lng, lat]", get_fill_color="color",
                     get_line_color=[255, 255, 255], line_width_min_pixels=1, stroked=True,
                     get_radius=600, radius_min_pixels=3, radius_max_pixels=9, pickable=True)


def _areas_layer(kind: str, highlight: str | None = None):
    items = db.areas(kind)
    feats = []
    for a in items:
        if not a.get("geojson") or not a["geojson"].get("type"):
            continue
        hl = a["name"] == highlight
        feats.append({"type": "Feature", "geometry": a["geojson"],
                      "properties": {"name": a["name"], "species": fmt(a["species"]),
                                     "observations": fmt(a["observations"]),
                                     "line": [214, 40, 40, 255] if hl else [90, 90, 90, 140],
                                     "lw": 3 if hl else 1}})
    if not feats:
        return None
    return pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feats}, id="areas",
                     stroked=True, filled=True, get_fill_color=[0, 0, 0, 0], get_line_color="properties.line",
                     get_line_width="properties.lw", line_width_units="pixels", pickable=False)


def observations_map(kind, name, *, taxon=None, user=None, quality=None, mode="auto", height=520,
                     key="map", borders: str | None = "region"):
    """Карта наблюдений: сетка (как на iNaturalist), теплокарта или точки."""
    layers = []
    if borders:
        bl = _areas_layer(borders, name if kind == borders else None)
        if bl:
            layers.append(bl)
    filtered = taxon or user or quality
    pts = None
    if mode == "auto":
        mode = "points" if filtered or kind != "all" else "grid"
    if mode in ("grid", "heat"):
        cells = db.map_cells(kind, name)
        layer = _grid_layer(cells) if mode == "grid" else _cells_layer(cells)
        if layer:
            layers.append(layer)
        tooltip = {"html": "Наблюдений в квадрате: <b>{n}</b>"} if mode == "grid" else None
    else:
        pts = db.map_points(kind, name, taxon=taxon, user=user, quality=quality)
        if not pts.empty:
            layers.append(_points_layer(pts))
        tooltip = {"html": "<b>{title}</b><br/><i>{sci}</i><br/>{user} · {date}",
                   "style": {"backgroundColor": "#fff", "color": "#333", "fontSize": "12px"}}
    deck = pdk.Deck(layers=layers, initial_view_state=KZ_VIEW, map_style="light", tooltip=tooltip)
    event = None
    try:
        event = st.pydeck_chart(deck, height=height, on_select="rerun", selection_mode="single-object", key=key)
    except TypeError:
        st.pydeck_chart(deck, height=height)
    if pts is not None:
        st.caption(f"Показано точек: {fmt(len(pts))}" + (" (последние 20 000)" if len(pts) >= 20000 else "")
                   + " · 🟢 исследовательский уровень · 🟡 требуется идентификация · ⚪ обыкновенное")
        # клик по точке → карточка наблюдения
        try:
            objs = event.selection.objects.get("points") if event else None
        except Exception:
            objs = None
        if objs:
            o = objs[0]
            st.success(f"**{o.get('title')}** *{o.get('sci') or ''}* — {o.get('user')}, {o.get('date')} · "
                       f"[открыть наблюдение ↗]({INAT}/observations/{o.get('id')})")


def choropleth(kind: str, highlight: str | None = None, height=520, key="choro"):
    items = db.areas(kind)
    if not items:
        st.info("Территории ещё не загружены.")
        return None
    vals = [a["species"] for a in items] or [0]
    lo, hi = min(vals), max(vals) or 1
    feats = []
    for a in items:
        if not a.get("geojson") or not a["geojson"].get("type"):
            continue
        t = (a["species"] - lo) / ((hi - lo) or 1)
        hl = a["name"] == highlight
        feats.append({"type": "Feature", "geometry": a["geojson"],
                      "properties": {"name": a["name"], "species": fmt(a["species"]),
                                     "observations": fmt(a["observations"]), "observers": fmt(a["observers"]),
                                     "fill": [int(232 - 150 * t), int(245 - 85 * t), int(205 - 195 * t), 200],
                                     "line": [214, 40, 40, 255] if hl else [80, 80, 80, 170],
                                     "lw": 3 if hl else 1}})
    layer = pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feats}, id="areas",
                      pickable=True, stroked=True, filled=True, auto_highlight=True,
                      get_fill_color="properties.fill", get_line_color="properties.line",
                      get_line_width="properties.lw", line_width_units="pixels")
    tooltip = {"html": "<b>{name}</b><br/>Видов: {species}<br/>Наблюдений: {observations}<br/>Наблюдателей: {observers}",
               "style": {"backgroundColor": "#fff", "color": "#333"}}
    deck = pdk.Deck(layers=[layer], initial_view_state=KZ_VIEW, map_style="light", tooltip=tooltip)
    try:
        ev = st.pydeck_chart(deck, height=height, on_select="rerun", selection_mode="single-object", key=key)
        objs = ev.selection.objects.get("areas") if ev else None
        if objs:
            props = objs[0].get("properties", objs[0])
            return props.get("name")
    except TypeError:
        st.pydeck_chart(deck, height=height)
    except Exception:
        pass
    return None


def footer():
    st.markdown("---")
    st.markdown(
        f'<span class="muted">Данные: <a href="{PROJECT_URL}" target="_blank">iNaturalist — проект «Флора Казахстана»</a>; '
        'фотографии принадлежат авторам наблюдений (лицензии CC на iNaturalist). '
        'Границы областей — geoBoundaries (2017, без областей Абай, Жетісу, Ұлытау); '
        'природные зоны — схематичные.</span>', unsafe_allow_html=True)


def empty_db_notice(s: dict) -> bool:
    if not s or not s.get("observations"):
        p = db.progress()
        st.info(f"Данные ещё загружаются: в базе {fmt(p.get('observations'))} наблюдений. "
                "Сводная статистика пересчитывается каждые 10 минут — обновите страницу чуть позже.")
        return True
    return False
