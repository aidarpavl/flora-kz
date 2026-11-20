import math

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import lang, t

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader(t("nav_observers"))
opts = [t("by_observations"), t("by_species")]
sort_label = st.radio(t("sort_by"), opts, horizontal=True, key=f"obsr_sort_{lang()}")
sort = "species" if sort_label == opts[1] else "observations"
PAGE = 100
key = f"obsr_page::{kind}:{name}:{sort}"
page = st.session_state.get(key, 1)
df, total = db.observers(kind, name, sort, PAGE, (page - 1) * PAGE)
if df.empty:
    st.info(t("no_data"))
else:
    c_obs, c_sp = t("observations_n").capitalize(), t("c_species").capitalize()
    tb = pd.DataFrame({
        t("rank"): range((page - 1) * PAGE + 1, (page - 1) * PAGE + 1 + len(df)),
        t("avatar"): df["icon"],
        t("observer"): df["user_login"],
        c_obs: df["observations"],
        c_sp: df["species"],
        t("profile"): ui.INAT + "/people/" + df["user_login"],
    })
    main = c_sp if sort == "species" else c_obs
    st.dataframe(tb, hide_index=True, use_container_width=True, height=700, column_config={
        t("avatar"): st.column_config.ImageColumn(width="small"),
        main: st.column_config.ProgressColumn(format="%d", min_value=0, max_value=int(tb[main].max())),
        t("profile"): st.column_config.LinkColumn(display_text="iNat ↗")})
    pages = max(1, math.ceil(total / PAGE))
    n1, n2, n3 = st.columns([1, 2, 1])
    n2.markdown(f"<div style='text-align:center'>{t('total', n=ui.fmt(total), p=page, pp=pages)}</div>",
                unsafe_allow_html=True)
    if n1.button(t("prev"), disabled=page <= 1, use_container_width=True):
        st.session_state[key] = page - 1
        st.rerun()
    if n3.button(t("next"), disabled=page >= pages, use_container_width=True):
        st.session_state[key] = page + 1
        st.rerun()
    with st.expander(t("observer_map")):
        who = st.selectbox(t("observer"), df["user_login"].tolist())
        ui.observations_map(kind, name, user=who, mode="points", key="observer_map", height=450)
ui.footer()
