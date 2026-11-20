"""Общие компоненты в стиле страницы проекта iNaturalist (двуязычные, карты — folium)."""
from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from urllib.parse import quote

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Fullscreen, HeatMap, MarkerCluster
from streamlit_folium import st_folium

from lib import db
from lib.i18n import area_name, lang, language_switch, t, taxon_name

GREEN = "#74AC00"
INAT = "https://www.inaturalist.org"
PROJECT_URL = f"{INAT}/projects/flora-kazahstana"
PLACEHOLDER = "https://static.inaturalist.org/images/iconic_taxa/plantae-200px.png"
USER_PLACEHOLDER = "https://static.inaturalist.org/attachment_defaults/users/icons/defaults/thumb.png"
KZ_CENTER, KZ_ZOOM = [48.2, 67.5], 5
RANKS = {"genus": ("Род", "Туыс"), "family": ("Семейство", "Тұқымдас"), "subfamily": ("Подсемейство", "Тұқымдас тармағы"),
         "tribe": ("Триба", "Триба"), "order": ("Порядок", "Қатар"), "class": ("Класс", "Класс"),
         "section": ("Секция", "Секция"), "subgenus": ("Подрод", "Туыс тармағы"), "hybrid": ("Гибрид", "Будан"),
         "complex": ("Комплекс", "Кешен"), "subspecies": ("Подвид", "Түршe"), "variety": ("Разновидность", "Әртүрлілік")}


ZONE_COLORS = {"Лесостепь": "#64990a", "Степь": "#c8f5c4", "Полупустыня": "#ffd83f",
               "Пустыня": "#fff28a", "Горы": "#c792d0"}


def zone_legend():
    from lib.i18n import lang as _lang
    items = db.areas("zone")
    order = ["Лесостепь", "Степь", "Полупустыня", "Пустыня", "Горы"]
    by = {a["name"]: a for a in items}
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;margin:0 14px 6px 0;font-size:.9rem">'
        f'<span style="width:28px;height:14px;border-radius:7px;background:{ZONE_COLORS[n]};'
        f'border:1px solid #999;margin-right:6px"></span>{esc(area_name(by[n]) if n in by else n)}'
        f'{" · " + fmt(by[n]["species"]) + " " + t("species_n") if n in by else ""}</span>'
        for n in order)
    st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)


def quality_labels() -> dict:
    return {"research": t("q_research"), "needs_id": t("q_needs_id"), "casual": t("q_casual")}


CSS = f"""
<style>
.block-container {{padding-top: 1rem; max-width: 1280px;}}
.banner {{display:flex; border-radius:4px; overflow:hidden; margin-bottom:14px; min-height:170px;}}
.banner .l {{flex:2; background:{GREEN} repeating-radial-gradient(circle at 30% 40%, rgba(255,255,255,.08) 0 2px, transparent 2px 22px);
             position:relative;}}
.banner .l .t {{position:absolute; left:22px; bottom:20px; background:#333; color:#fff; font-size:1.6rem; padding:6px 14px;}}
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
.desc {{background:#f7faf0; border-left:4px solid {GREEN}; padding:10px 14px; font-size:.95rem; line-height:1.5;}}
</style>
"""


# ---------- форматирование ----------

def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def esc(s) -> str:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    return html.escape(str(s))


def ago(ts) -> str:
    if not ts:
        return ""
    try:
        d = (datetime.now(timezone.utc) - pd.to_datetime(ts, utc=True).to_pydatetime()).days
    except Exception:
        return ""
    kk = lang() == "kk"
    if d < 1:
        return "бүгін" if kk else "сегодня"
    if d < 30:
        return f"{d} күн" if kk else f"{d} дн"
    if d < 365:
        return f"{d // 30} ай" if kk else f"{d // 30}мес"
    return f"{d // 365} жыл" if kk else f"{d // 365}г"


def obs_title(row) -> tuple[str, str]:
    """(общее название, научное с рангом) для наблюдения iNaturalist."""
    common = row.get("obs_common_name") or ""
    sci = row.get("obs_taxon_name") or ("Белгісіз" if lang() == "kk" else "Неизвестно")
    rank = row.get("obs_taxon_rank") or ""
    sci_full = f"{RANKS[rank][1 if lang() == 'kk' else 0]} {sci}" if rank in RANKS else sci
    return (common or sci_full), (sci_full if common else "")


# ---------- территория и язык ----------

def scope() -> tuple[str, str]:
    if "scope" not in st.session_state:
        qp = st.query_params.get("scope", "all:all")
        kind, _, name = qp.partition(":")
        st.session_state.scope = (kind or "all", name or "all")
    return st.session_state.scope


def scope_label(kind, name) -> str:
    if kind == "all":
        return t("all_kz")
    for a in db.areas(kind):
        if a["name"] == name:
            return area_name(a)
    return name


def sidebar():
    with st.sidebar:
        st.markdown(f"### 🌐 {t('language')}")
        language_switch()
        st.markdown(f"### 🗺️ {t('territory')}")
        kind, name = scope()
        options = [t("all_kz"), t("region"), t("zone")]
        idx = {"all": 0, "region": 1, "zone": 2}.get(kind, 0)
        mode = st.radio(t("territory"), options, index=idx, label_visibility="collapsed")
        if mode == options[0]:
            new = ("all", "all")
        else:
            k = "region" if mode == options[1] else "zone"
            items = db.areas(k)
            names = [a["name"] for a in items]
            if not names:
                st.info(t("not_loaded"))
                new = ("all", "all")
            else:
                labels = {a["name"]: f'{area_name(a)} · {fmt(a["species"])} {t("species_n")}' for a in items}
                cur = name if (kind == k and name in names) else names[0]
                sel = st.selectbox(mode, names, index=names.index(cur), format_func=labels.get)
                new = (k, sel)
        if new != st.session_state.scope:
            st.session_state.scope = new
            st.query_params["scope"] = f"{new[0]}:{new[1]}"
            st.rerun()
        st.caption(t("filter_hint"))
        p = db.progress()
        if p:
            st.markdown("---")
            st.caption(t("in_db", o=fmt(p.get("observations")), t=fmt(p.get("taxa"))))
        if st.session_state.get("editor_pwd"):
            st.success(f"✏️ {t('logged_in')}")
        st.markdown(f"[iNaturalist ↗]({PROJECT_URL})")


def setup():
    st.markdown(CSS, unsafe_allow_html=True)


def header():
    kind, name = scope()
    s = db.stats(kind, name)
    st.markdown(
        f"""<div class="banner"><div class="l"><div class="t">{esc(t('title'))}</div></div>
        <div class="r"><h3>{esc(t('about'))}</h3>{esc(t('about_text'))}<br><br>
        <a href="{PROJECT_URL}" target="_blank">{esc(t('open_inat'))}</a></div></div>
        <div class="counters">
          <div class="c"><div class="n">{fmt(s.get('observations'))}</div><div class="l">{t('c_observations')}</div></div>
          <div class="c"><div class="n">{fmt(s.get('species'))}</div><div class="l">{t('c_species')}</div></div>
          <div class="c"><div class="n">{fmt(s.get('identifiers'))}</div><div class="l">{t('c_identifiers')}</div></div>
          <div class="c"><div class="n">{fmt(s.get('observers'))}</div><div class="l">{t('c_observers')}</div></div>
          <div class="scope">📍 {esc(scope_label(kind, name))}</div>
        </div>""", unsafe_allow_html=True)
    return s


def empty_db_notice(s: dict) -> bool:
    if not s or not s.get("observations"):
        st.info(t("loading_db", o=fmt(db.progress().get("observations"))))
        return True
    return False


def footer():
    st.markdown("---")
    st.markdown(f'<span class="muted">{esc(t("footer"))}</span>', unsafe_allow_html=True)


# ---------- карточки ----------

def taxon_link(taxon_id) -> str:
    kind, name = scope()
    return f"./taxon?id={taxon_id}&scope={quote(kind + ':' + name)}&lang={lang()}"


def species_cards(df: pd.DataFrame):
    if df.empty:
        st.info(t("not_found"))
        return
    parts = []
    for _, r in df.iterrows():
        img = r.get("photo_url") or PLACEHOLDER
        parts.append(
            f'<div class="card"><a href="{taxon_link(r["taxon_id"])}" target="_self">'
            f'<div class="ph" style="background-image:url(\'{esc(img)}\')">'
            f'<div class="badge">{fmt(r.get("n"))} {t("observations_n")}</div></div>'
            f'<div class="b"><div class="cn">{esc(taxon_name(r))}</div><div class="sn">{esc(r.get("name"))}</div></div></a></div>')
    st.markdown(f'<div class="grid">{"".join(parts)}</div>', unsafe_allow_html=True)


def observation_cards(df: pd.DataFrame):
    if df.empty:
        st.info(t("not_found"))
        return
    parts = []
    for _, r in df.iterrows():
        cn, sn = obs_title(r)
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


def board(title: str, rows: list[tuple], square=False):
    items = "".join(
        f'<div class="row"><img class="{"sq" if square else ""}" src="{esc(img) or USER_PLACEHOLDER}">'
        f'<a href="{esc(link)}" target="{"_self" if str(link).startswith("./") else "_blank"}">{esc(label)}</a>'
        f'<span class="v">{esc(val)}</span></div>'
        for img, label, link, val in rows)
    st.markdown(f'<div class="board"><h4>{esc(title)}</h4>{items or "<span class=muted>" + t("no_data") + "</span>"}</div>',
                unsafe_allow_html=True)


# ---------- карты (folium: спутник / рельеф / схема) ----------

def base_map(center=None, zoom=None, height_hint=None) -> folium.Map:
    m = folium.Map(location=center or KZ_CENTER, zoom_start=zoom or KZ_ZOOM, tiles=None, control_scale=True,
                   prefer_canvas=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics", name=f"🛰️ {t('satellite')}", max_zoom=19).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="🏷️ Подписи / Жазулар", overlay=True, control=True, opacity=0.9).add_to(m)
    folium.TileLayer("OpenTopoMap", name=f"⛰️ {t('terrain')}", max_zoom=17,
                     attr="© OpenStreetMap, SRTM | © OpenTopoMap (CC-BY-SA)").add_to(m)
    folium.TileLayer("CartoDB positron", name=f"🗺️ {t('scheme')}").add_to(m)
    Fullscreen(position="topleft").add_to(m)
    return m


def add_borders(m: folium.Map, kind: str = "region", highlight: str | None = None, choropleth=False):
    items = db.areas(kind)
    if not items:
        return
    vals = [a["species"] for a in items] or [0]
    lo, hi = min(vals), max(vals) or 1
    feats = []
    for a in items:
        if not a.get("geojson") or not a["geojson"].get("type"):
            continue
        k = (a["species"] - lo) / ((hi - lo) or 1)
        feats.append({"type": "Feature", "geometry": a["geojson"], "properties": {
            "key": a["name"], "title": area_name(a), "species": fmt(a["species"]),
            "observations": fmt(a["observations"]), "observers": fmt(a["observers"]),
            "fill": ZONE_COLORS.get(a["name"]) if kind == "zone" else
                    f"#{int(232 - 150 * k):02x}{int(245 - 85 * k):02x}{int(205 - 195 * k):02x}"}})
    fc = {"type": "FeatureCollection", "features": feats}

    def style(f):
        hl = f["properties"]["key"] == highlight
        zone_fill = kind == "zone"
        return {"color": "#ff3b30" if hl else ("#555555" if zone_fill else "#ffffff"),
                "weight": 3 if hl else (0.8 if zone_fill else 1.2),
                "fillColor": f["properties"]["fill"] if (choropleth or zone_fill) else "#000000",
                "fillOpacity": (0.7 if choropleth else 0.35) if zone_fill else (0.55 if choropleth else 0.0),
                "opacity": 0.9}

    folium.GeoJson(
        fc, name=t("regions") if kind == "region" else t("zones"), style_function=style,
        highlight_function=lambda f: {"weight": 3, "color": "#ffd60a"},
        tooltip=folium.GeoJsonTooltip(fields=["title", "species", "observations"],
                                      aliases=["", t("c_species").capitalize() + ":", t("c_observations").capitalize() + ":"]),
    ).add_to(m)


_POINT_CB = """
function (row) {
  var c = row[5] == 'research' ? '#74AC00' : (row[5] == 'needs_id' ? '#f5c400' : '#bbbbbb');
  var m = L.circleMarker(new L.LatLng(row[0], row[1]), {radius: 6, color: '#fff', weight: 1, fillColor: c, fillOpacity: 0.95});
  m.bindPopup('<b>' + row[2] + '</b><br><i>' + (row[3] || '') + '</i><br>' + (row[6] || '') + ' · ' + (row[7] || '') +
              '<br><a href="https://www.inaturalist.org/observations/' + row[4] + '" target="_blank">iNaturalist ↗</a>');
  return m;
}
"""


def add_points(m: folium.Map, pts: pd.DataFrame):
    if pts.empty:
        return
    data = pts[["lat", "lng", "title", "sci", "id", "quality", "user", "date"]].fillna("").values.tolist()
    from folium.plugins import FastMarkerCluster
    FastMarkerCluster(data, callback=_POINT_CB, name=t("map_points"),
                      options={"maxClusterRadius": 45, "disableClusteringAtZoom": 10}).add_to(m)


def add_user_points(m: folium.Map, df: pd.DataFrame):
    if df is None or df.empty:
        return
    fg = folium.FeatureGroup(name="🔵 " + t("user_obs"))
    for _, r in df.iterrows():
        title = r["name_kk"] if lang() == "kk" else r["name_ru"]
        desc = r.get("description_kk") if lang() == "kk" else r.get("description_ru")
        popup = (f"<b>{esc(title)}</b><br><i>{esc(r.get('sci'))} {esc(r.get('subspecies') or '')}</i><br>"
                 f"{esc(r.get('author') or '')} · {esc(r.get('observed_on') or '')}<br>{esc((desc or '')[:200])}")
        folium.CircleMarker([r["lat"], r["lng"]], radius=8, color="#fff", weight=2, fill=True,
                            fill_color="#1e88e5", fill_opacity=0.95, popup=folium.Popup(popup, max_width=280)).add_to(fg)
    fg.add_to(m)


def show_map(m: folium.Map, key: str, height=540, returned=None):
    folium.LayerControl(collapsed=True).add_to(m)
    return st_folium(m, height=height, use_container_width=True, key=key,
                     returned_objects=returned or [])


def observations_map(kind, name, *, taxon=None, user=None, quality=None, mode="auto", height=540,
                     key="map", borders: str | None = "region", limit=15000):
    """Карта наблюдений: кластеры точек (как на iNaturalist) или теплокарта."""
    m = base_map()
    if borders:
        add_borders(m, borders, name if kind == borders else None)
    if mode == "auto":
        mode = "points"
    if mode == "heat":
        cells = db.map_cells(kind, name)
        if not cells.empty:
            mx = float(cells["n"].max()) or 1.0
            HeatMap([[r.lat, r.lng, math.log1p(r.n) / math.log1p(mx)] for r in cells.itertuples()],
                    name=t("map_heat"), radius=14, blur=12, min_opacity=0.35, max_zoom=9).add_to(m)
    else:
        pts = db.map_points(kind, name, taxon=taxon, user=user, quality=quality, limit=limit)
        add_points(m, pts)
        st.caption(t("shown_points", n=fmt(len(pts))) + " · " + t("legend_q"))
    add_user_points(m, db.user_observations(taxon=taxon, kind=kind, name=name))
    show_map(m, key=key, height=height)


def territory_map(kind: str, highlight: str | None, key: str, height=560) -> str | None:
    """Хороплет областей/зон; возвращает ключ территории, по которой кликнули."""
    m = base_map()
    add_borders(m, kind, highlight, choropleth=True)
    out = show_map(m, key=key, height=height, returned=["last_active_drawing"])
    try:
        return (out or {}).get("last_active_drawing", {}).get("properties", {}).get("key")
    except Exception:
        return None
