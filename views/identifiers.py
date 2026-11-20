import math

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import t

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader(t("identifiers_title"))
st.caption(t("identifiers_hint"))
PAGE = 100
key = f"id_page::{kind}:{name}"
page = st.session_state.get(key, 1)
df, total = db.identifiers(kind, name, PAGE, (page - 1) * PAGE)
if df.empty:
    st.info(t("ident_loading"))
else:
    tb = pd.DataFrame({
        t("rank"): range((page - 1) * PAGE + 1, (page - 1) * PAGE + 1 + len(df)),
        t("nav_identifiers"): df["user_login"],
        t("identifications"): df["identifications"],
        t("profile"): ui.INAT + "/people/" + df["user_login"],
    })
    st.dataframe(tb, hide_index=True, use_container_width=True, height=700, column_config={
        t("identifications"): st.column_config.ProgressColumn(format="%d", min_value=0,
                                                              max_value=int(df["identifications"].max())),
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
ui.footer()
