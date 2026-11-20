import math

import pandas as pd
import streamlit as st

from lib import db, ui

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader("Наблюдатели")
sort_label = st.radio("Сортировать по", ["Наблюдениям", "Видам"], horizontal=True)
sort = "species" if sort_label == "Видам" else "observations"
PAGE = 100
key = f"ob_page::{kind}:{name}:{sort}"
page = st.session_state.get(key, 1)
df, total = db.observers(kind, name, sort, PAGE, (page - 1) * PAGE)
if df.empty:
    st.info("Нет данных.")
else:
    t = pd.DataFrame({
        "Место": range((page - 1) * PAGE + 1, (page - 1) * PAGE + 1 + len(df)),
        "Аватар": df["icon"],
        "Наблюдатель": df["user_login"],
        "Наблюдений": df["observations"],
        "Видов": df["species"],
        "Профиль": ui.INAT + "/people/" + df["user_login"],
    })
    main = "Видов" if sort == "species" else "Наблюдений"
    st.dataframe(t, hide_index=True, use_container_width=True, height=700,
                 column_config={
                     "Аватар": st.column_config.ImageColumn(width="small"),
                     main: st.column_config.ProgressColumn(format="%d", min_value=0,
                                                           max_value=int(t[main].max())),
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

    with st.expander("🗺️ Наблюдения выбранного наблюдателя на карте"):
        who = st.selectbox("Наблюдатель", df["user_login"].tolist())
        ui.observations_map(kind, name, user=who, mode="points", key="observer_map", height=450)
ui.footer()
