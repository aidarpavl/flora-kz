"""Флора Казахстана / Қазақстан флорасы — Streamlit-приложение (точка входа)."""
import streamlit as st

st.set_page_config(page_title="Флора Казахстана · Қазақстан флорасы", page_icon="🌿", layout="wide")

from lib import ui  # noqa: E402
from lib.i18n import lang, t  # noqa: E402
from lib import basemaps, session  # noqa: E402

ui.base_map = basemaps.base_map   # подложки: CARTO только с ключом CARTO_KEY, иначе OpenStreetMap

ui.setup()
session.restore()   # вход из cookie — не «вылетать» при переходе по ссылкам

pages = [
    st.Page("views/overview.py", title=t("nav_overview"), icon="🏠", default=True),
    st.Page("views/observations.py", title=t("nav_observations"), icon="📷", url_path="observations"),
    st.Page("views/species.py", title=t("nav_species"), icon="🌿", url_path="species"),
    st.Page("views/identifiers.py", title=t("nav_identifiers"), icon="🔬", url_path="identifiers"),
    st.Page("views/observers.py", title=t("nav_observers"), icon="👥", url_path="observers"),
    st.Page("views/stats.py", title=t("nav_stats"), icon="📊", url_path="stats"),
    st.Page("views/territories.py", title=t("nav_territories"), icon="🗺️", url_path="territories"),
    st.Page("views/redbook.py", title=t("nav_redbook"), icon="🌺", url_path="redbook"),
    st.Page("views/rb_species.py", title=("Қызыл кітап түрі" if lang() == "kk" else "Вид Красной книги"), icon="🌺", url_path="rb_species"),
    st.Page("views/taxon.py", title=t("nav_taxon"), icon="🔎", url_path="taxon"),
    st.Page("views/add.py", title=t("nav_add"), icon="➕", url_path="add"),
    st.Page("views/editor.py", title=t("nav_editor"), icon="✏️", url_path="editor"),
    st.Page("views/account.py", title=t("nav_account"), icon="👤", url_path="account"),
]
try:
    nav = st.navigation(pages, position="top")
except TypeError:
    nav = st.navigation(pages)
ui.sidebar()   # после st.navigation: ссылки st.page_link работают только на зарегистрированные страницы
session.sync_cookie()
nav.run()
