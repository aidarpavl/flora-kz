import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import area_name, t

kind, name = ui.scope()
ui.header()

st.subheader(t("nav_territories"))
opts = [t("regions"), t("zones")]
mode = st.radio("split", opts, horizontal=True, index=1 if kind == "zone" else 0, label_visibility="collapsed")
k = "region" if mode == opts[0] else "zone"
st.caption(t("territories_hint"))
if k == "zone":
    ui.zone_legend()
clicked = ui.territory_map(k, name if kind == k else None, key=f"terr_{k}")
if clicked and (k, clicked) != (kind, name):
    st.session_state.scope = (k, clicked)
    st.query_params["scope"] = f"{k}:{clicked}"
    st.rerun()

items = db.areas(k)
if items:
    a = pd.DataFrame([{t("territory"): area_name(x), t("c_species").capitalize(): x["species"],
                       t("observations_n").capitalize(): x["observations"], t("observers_n"): x["observers"]}
                      for x in items])
    col = t("c_species").capitalize()
    st.dataframe(a, hide_index=True, use_container_width=True, column_config={
        col: st.column_config.ProgressColumn(format="%d", min_value=0, max_value=int(a[col].max() or 1))})

if kind != "all":
    st.subheader(ui.scope_label(kind, name))
    ui.observations_map(kind, name, mode="points", key="terr_points", borders=kind)
    if st.button(t("reset_filter")):
        st.session_state.scope = ("all", "all")
        st.query_params["scope"] = "all:all"
        st.rerun()
ui.footer()
