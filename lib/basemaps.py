"""Подложки карт. CARTO (Voyager, Positron, подписи) с 2026 г. требует бесплатный ключ:
https://carto.com/basemaps/apikey — добавьте его в Secrets приложения как CARTO_KEY = "…".
Без ключа по умолчанию открывается OpenStreetMap, а слои CARTO не показываются (иначе — водяной знак)."""
import folium
import streamlit as st
from folium.plugins import Fullscreen

from lib.i18n import lang, t

KZ_CENTER, KZ_ZOOM = [48.2, 67.5], 5
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"


def carto_key() -> str:
    try:
        return str(st.secrets.get("CARTO_KEY", "") or "").strip()
    except Exception:
        return ""


def base_map(center=None, zoom=None, height_hint=None) -> folium.Map:
    kk = lang() == "kk"
    key = carto_key()
    m = folium.Map(location=center or KZ_CENTER, zoom_start=zoom or KZ_ZOOM, tiles=None, control_scale=True,
                   prefer_canvas=True)
    carto = "&copy; OpenStreetMap contributors &copy; CARTO"
    q = f"?key={key}" if key else ""
    if key:   # 1. Voyager (по умолчанию, если есть ключ)
        folium.TileLayer(f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{{z}}/{{x}}/{{y}}{{r}}.png{q}",
                         attr=carto, name="🗺️ Voyager (OSM)", subdomains="abcd", max_zoom=20).add_to(m)
    # 2. OpenStreetMap стандарт (по умолчанию без ключа)
    folium.TileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", attr="&copy; OpenStreetMap contributors",
                     name="🌍 OpenStreetMap", max_zoom=19, show=not key).add_to(m)
    # 3. Светлая: Carto Positron (с ключом) или Esri Light Gray
    if key:
        folium.TileLayer(f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png{q}", attr=carto,
                         name=f"⚪ {'Ашық' if kk else 'Светлая'} (Carto Positron)", subdomains="abcd", max_zoom=20,
                         show=False).add_to(m)
    else:
        folium.TileLayer(f"{ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}", attr="Esri, HERE, Garmin, OSM",
                         name=f"⚪ {'Ашық' if kk else 'Светлая'} (Esri)", max_zoom=16, show=False).add_to(m)
    # 4. 2ГИС (растровые тайлы)
    folium.TileLayer("https://tile{s}.maps.2gis.com/tiles?x={x}&y={y}&z={z}&v=1.1", attr="&copy; 2ГИС",
                     name="🟢 2ГИС", subdomains="0123", max_zoom=18, show=False).add_to(m)
    # спутник и рельеф
    folium.TileLayer(f"{ESRI}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}", attr="Esri, Maxar, Earthstar Geographics",
                     name=f"🛰️ {t('satellite')}", max_zoom=19, show=False).add_to(m)
    folium.TileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", name=f"⛰️ {t('terrain')}", max_zoom=17,
                     subdomains="abc", attr="&copy; OpenStreetMap, SRTM | &copy; OpenTopoMap (CC-BY-SA)",
                     show=False).add_to(m)
    # подписи поверх слоёв данных (отдельная панель): Voyager labels с ключом, иначе подписи Esri (выкл.)
    folium.map.CustomPane("labels", z_index=650, pointer_events=False).add_to(m)
    label_name = "🏷️ " + ("Жазулар" if kk else "Подписи")
    if key:
        folium.TileLayer(f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png{q}",
                         attr=carto, name=label_name, subdomains="abcd", overlay=True, control=True, pane="labels",
                         max_zoom=20).add_to(m)
    else:
        folium.TileLayer(f"{ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}", attr="Esri",
                         name=label_name, overlay=True, control=True, pane="labels", max_zoom=19, show=False).add_to(m)
    Fullscreen(position="topleft").add_to(m)
    return m
