import streamlit as st

from lib import db, ui
from lib.i18n import t

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

q = st.text_input(t("species_search"), key="sp_q")
STEP = 48
key = f"sp_limit::{kind}:{name}:{q}"
limit = st.session_state.get(key, STEP)
df, total = db.species(kind, name, q, limit, 0)
st.markdown(f"**{ui.fmt(total)}** {t('c_species')} · {ui.scope_label(kind, name)} · {t('by_obs')}")
ui.species_cards(df)
st.write("")
if len(df) < total:
    if st.button(t("show_more", n=ui.fmt(total - len(df))), use_container_width=True):
        st.session_state[key] = limit + STEP
        st.rerun()

with st.expander(t("csv")):
    if st.button(t("prepare")):
        full, _ = db.species(kind, name, q, 100000, 0)
        cols = ["taxon_id", "name", "common_name_ru", "common_name_kk", "common_name_en", "family", "n", "inat_url"]
        st.download_button(t("download"), full[[c for c in cols if c in full]].to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"flora_kz_{name}.csv", mime="text/csv")
ui.footer()
