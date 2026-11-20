import pandas as pd
import streamlit as st

from lib import db, ui

kind, name = ui.scope()
ui.header()

st.subheader("Карта территорий")
mode = st.radio("Разделение", ["Области", "Природные зоны"], horizontal=True,
                index=1 if kind == "zone" else 0)
k = "region" if mode == "Области" else "zone"
st.caption("Цвет — число видов (темнее — больше). Нажмите на территорию, чтобы выбрать её для всех вкладок.")
clicked = ui.choropleth(k, highlight=name if kind == k else None, key=f"choro_{k}")
if clicked and (k, clicked) != (kind, name):
    st.session_state.scope = (k, clicked)
    st.query_params["scope"] = f"{k}:{clicked}"
    st.rerun()

a = pd.DataFrame(db.areas(k))
if not a.empty:
    t = a[["name", "species", "observations", "observers"]].rename(columns={
        "name": "Территория", "species": "Видов", "observations": "Наблюдений", "observers": "Наблюдателей"})
    st.dataframe(t, hide_index=True, use_container_width=True,
                 column_config={"Видов": st.column_config.ProgressColumn(
                     format="%d", min_value=0, max_value=int(t["Видов"].max() or 1))})

if kind != "all":
    st.subheader(f"Наблюдения: {name}")
    ui.observations_map(kind, name, mode="points", key="terr_points", borders=kind)
    if st.button("Сбросить фильтр — весь Казахстан"):
        st.session_state.scope = ("all", "all")
        st.query_params["scope"] = "all:all"
        st.rerun()
ui.footer()
