import math

import streamlit as st

from lib import db, ui

ui.hero("Виды", "Список видов растений для выбранной территории — как вкладка «Виды» на iNaturalist")

c1, c2 = st.columns([3, 2])
with c1:
    kind, name = ui.territory_picker("sp")
with c2:
    q = st.text_input("Поиск (латынь, русское название, семейство)", key="sp_q")
    per_row = st.select_slider("Карточек в ряду", [4, 5, 6, 8], value=6, key="sp_cols")

PAGE = per_row * 6
state_key = f"sp_page::{kind}::{name}::{q}"
page = st.session_state.get(state_key, 1)

df, total = db.species_list(kind, name, q, PAGE, (page - 1) * PAGE)
pages = max(1, math.ceil(total / PAGE))
where = "Весь Казахстан" if kind == "all" else name
st.markdown(f"**{total}** видов · {where}")

if df.empty:
    st.info("Ничего не найдено.")
else:
    for start in range(0, len(df), per_row):
        cols = st.columns(per_row)
        for col, (_, r) in zip(cols, df.iloc[start:start + per_row].iterrows()):
            with col:
                st.markdown(ui.species_card(r), unsafe_allow_html=True)
                if st.button("Подробнее", key=f"more_{r['id']}", use_container_width=True):
                    st.session_state["taxon_id"] = int(r["id"])
                    st.switch_page("views/taxon.py")

nav = st.columns([1, 2, 1])
if nav[0].button("← Назад", disabled=page <= 1, use_container_width=True):
    st.session_state[state_key] = page - 1
    st.rerun()
nav[1].markdown(f"<div style='text-align:center'>Страница {page} из {pages}</div>", unsafe_allow_html=True)
if nav[2].button("Вперёд →", disabled=page >= pages, use_container_width=True):
    st.session_state[state_key] = page + 1
    st.rerun()

with st.expander("Скачать список видов (CSV)"):
    if st.button("Подготовить файл"):
        full, _ = db.species_list(kind, name, q, 100000, 0)
        st.download_button("Скачать CSV",
                           full.drop(columns=["total_count"]).to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"flora_kz_{where}.csv", mime="text/csv")

ui.footer()
