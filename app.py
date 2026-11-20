"""Флора Казахстана / Қазақстан флорасы — Streamlit-приложение (точка входа)."""
import streamlit as st

st.set_page_config(page_title="Флора Казахстана · Қазақстан флорасы", page_icon="🌿", layout="wide")

from lib import ui  # noqa: E402
from lib.i18n import t  # noqa: E402

ui.setup()
ui.sidebar()

pages = [
    st.Page("views/overview.py", title=t("nav_overview"), icon="🏠", default=True),
    st.Page("views/observations.py", title=t("nav_observations"), icon="📷", url_path="observations"),
    st.Page("views/species.py", title=t("nav_species"), icon="🌿", url_path="species"),
    st.Page("views/identifiers.py", title=t("nav_identifiers"), icon="🔬", url_path="identifiers"),
    st.Page("views/observers.py", title=t("nav_observers"), icon="👥", url_path="observers"),
    st.Page("views/stats.py", title=t("nav_stats"), icon="📊", url_path="stats"),
    st.Page("views/territories.py", title=t("nav_territories"), icon="🗺️", url_path="territories"),
    st.Page("views/taxon.py", title=t("nav_taxon"), icon="🔎", url_path="taxon"),
    st.Page("views/add.py", title=t("nav_add"), icon="➕", url_path="add"),
    st.Page("views/editor.py", title=t("nav_editor"), icon="✏️", url_path="editor"),
]
try:
    nav = st.navigation(pages, position="top")
except TypeError:
    nav = st.navigation(pages)
nav.run()
