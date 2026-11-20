import math

import pandas as pd
import streamlit as st

from lib import db, ui

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader("Эксперты (определители)")
st.caption("Число определений, сделанных для чужих наблюдений проекта на выбранной территории.")
PAGE = 100
key = f"id_page::{kind}:{name}"
page = st.session_state.get(key, 1)
df, total = db.identifiers(kind, name, PAGE, (page - 1) * PAGE)
if df.empty:
    st.info("Определения ещё загружаются — они появятся после полного обновления данных.")
else:
    t = pd.DataFrame({
        "Место": range((page - 1) * PAGE + 1, (page - 1) * PAGE + 1 + len(df)),
        "Эксперт": df["user_login"],
        "Определений": df["identifications"],
        "Профиль": ui.INAT + "/people/" + df["user_login"],
    })
    st.dataframe(t, hide_index=True, use_container_width=True, height=700,
                 column_config={
                     "Определений": st.column_config.ProgressColumn(
                         format="%d", min_value=0, max_value=int(df["identifications"].max())),
                     "Профиль": st.column_config.LinkColumn(display_text="iNat ↗")})
    pages = max(1, math.ceil(total / PAGE))
    n1, n2, n3 = st.columns([1, 2, 1])
    n2.markdown(f"<div style='text-align:center'>Всего {ui.fmt(total)} · стр. {page} из {pages}</div>",
                unsafe_allow_html=True)
    if n1.button("← Назад", disabled=page <= 1, use_container_width=True):
        st.session_state[key] = page - 1
        st.rerun()
    if n3.button("Вперёд →", disabled=page >= pages, use_container_width=True):
        st.session_state[key] = page + 1
        st.rerun()
ui.footer()
