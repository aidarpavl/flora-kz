import streamlit as st

from lib import db, ui

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

c1, c2 = st.columns([3, 1])
q = c1.text_input("Поиск вида (латынь, русское или английское название, семейство)", key="sp_q")
c2.write("")
STEP = 48
key = f"sp_limit::{kind}:{name}:{q}"
limit = st.session_state.get(key, STEP)
df, total = db.species(kind, name, q, limit, 0)
st.markdown(f"**{ui.fmt(total)}** видов · {ui.scope_label(kind, name)} · по числу наблюдений")
ui.species_cards(df)
st.write("")
if len(df) < total:
    if st.button(f"Показать ещё ({ui.fmt(total - len(df))} осталось)", use_container_width=True):
        st.session_state[key] = limit + STEP
        st.rerun()

with st.expander("⬇️ Скачать список видов (CSV)"):
    if st.button("Подготовить файл"):
        full, _ = db.species(kind, name, q, 100000, 0)
        cols = ["taxon_id", "name", "common_name_ru", "common_name_en", "family", "n", "inat_url"]
        st.download_button("Скачать CSV", full[[c for c in cols if c in full]].to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"flora_kz_{ui.scope_label(kind, name)}.csv", mime="text/csv")
ui.footer()
