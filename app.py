"""Флора Казахстана — Streamlit-приложение (точка входа)."""
import streamlit as st

st.set_page_config(page_title="Флора Казахстана", page_icon="🌿", layout="wide")

from lib import ui  # noqa: E402

ui.setup()
ui.sidebar_scope()

pages = [
    st.Page("views/overview.py", title="Обзор", icon="🏠", default=True),
    st.Page("views/observations.py", title="Наблюдения", icon="📷", url_path="observations"),
    st.Page("views/species.py", title="Виды", icon="🌿", url_path="species"),
    st.Page("views/identifiers.py", title="Эксперты", icon="🔬", url_path="identifiers"),
    st.Page("views/observers.py", title="Наблюдатели", icon="👥", url_path="observers"),
    st.Page("views/stats.py", title="Статистика", icon="📊", url_path="stats"),
    st.Page("views/territories.py", title="Карта территорий", icon="🗺️", url_path="territories"),
    st.Page("views/taxon.py", title="Вид", icon="🔎", url_path="taxon"),
]
try:
    nav = st.navigation(pages, position="top")
except TypeError:  # старые версии Streamlit
    nav = st.navigation(pages)
nav.run()
