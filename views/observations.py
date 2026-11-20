import math

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import lang, t

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader(t("nav_observations"))
ql = ui.quality_labels()
f1, f2, f3, f4 = st.columns([3, 2, 2, 3])
q = f1.text_input(t("taxon_search"), key="ob_q")
quality_label = f2.selectbox(t("quality"), [t("any")] + list(ql.values()), key=f"ob_qual_{lang()}")
quality = {v: k for k, v in ql.items()}.get(quality_label)
user = f3.text_input(t("observer_login"), key="ob_user").strip() or None
dates = f4.date_input(t("period"), value=(), key="ob_dates", format="DD.MM.YYYY")
d_from = dates[0] if len(dates) > 0 else None
d_to = dates[1] if len(dates) > 1 else None

taxon_id = None
if q:
    found = db.search_taxa(q)
    if not found.empty:
        opts = {0: t("all_by_query", q=q)}
        for _, r in found.iterrows():
            cn = (r.get("common_name_kk") or r.get("common_name_ru")) if lang() == "kk" else r.get("common_name_ru")
            opts[int(r["id"])] = f'{cn or ""} {r["name"]}'.strip()
        taxon_id = st.selectbox(t("refine_species"), list(opts), format_func=opts.get, key="ob_taxon") or None

views = [t("view_map"), t("view_grid"), t("view_table")]
view = st.radio("view", views, horizontal=True, index=1, key=f"ob_view_{lang()}", label_visibility="collapsed")

if view == views[0]:
    ui.observations_map(kind, name, taxon=taxon_id, user=user, quality=quality, mode="points", key="obs_map",
                        borders="zone" if kind == "zone" else "region")
else:
    PAGE = 48 if view == views[1] else 100
    key = f"ob_page::{kind}:{name}:{q}:{taxon_id}:{quality}:{user}:{d_from}:{d_to}:{view}"
    page = st.session_state.get(key, 1)
    df, total = db.observations(kind, name, taxon=taxon_id, user=user, quality=quality,
                                q=None if taxon_id else q, date_from=d_from, date_to=d_to,
                                limit=PAGE, offset=(page - 1) * PAGE)
    pages = max(1, math.ceil(total / PAGE))
    filtered = taxon_id or user or quality or q or d_from or d_to
    shown = t("more_than_10k") if total > 10000 and filtered else ui.fmt(total)
    st.markdown(f"**{shown}** {t('observations_n')} · {t('page_of', p=page, n=ui.fmt(pages))}")
    if view == views[1]:
        ui.observation_cards(df)
    elif not df.empty:
        tb = pd.DataFrame({
            t("photo"): df["photo_url"],
            t("name"): [ui.obs_title(r)[0] for _, r in df.iterrows()],
            t("scientific"): df["obs_taxon_name"],
            t("observer"): df["user_login"],
            t("date"): df["observed_on"],
            t("place"): df["place_guess"],
            t("region"): df["region"],
            t("zone"): df["zone"],
            t("quality"): df["quality_grade"].map(ql),
            t("link"): df["uri"],
        })
        st.dataframe(tb, hide_index=True, use_container_width=True, height=600,
                     column_config={t("photo"): st.column_config.ImageColumn(width="small"),
                                    t("link"): st.column_config.LinkColumn(display_text="iNat ↗")})
    n1, _, n3 = st.columns([1, 2, 1])
    if n1.button(t("prev"), disabled=page <= 1, use_container_width=True):
        st.session_state[key] = page - 1
        st.rerun()
    if n3.button(t("next"), disabled=page >= pages, use_container_width=True):
        st.session_state[key] = page + 1
        st.rerun()
ui.footer()
