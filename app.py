"""Флора Казахстана — Streamlit-приложение (точка входа)."""
import streamlit as st

st.set_page_config(page_title="Флора Казахстана", page_icon="🌿", layout="wide")

from lib import ui  # noqa: E402

ui.setup()

pages = [
    st.Page("views/overview.py", title="Обзор", icon="🏠", default=True),
    st.Page("views/species.py", title="Виды", icon="🌿", url_path="species"),
    st.Page("views/map.py", title="Карта", icon="🗺️", url_path="map"),
    st.Page("views/taxon.py", title="Вид", icon="🔎", url_path="taxon"),
]
st.navigation(pages).run()
