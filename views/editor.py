from datetime import date

import pandas as pd

import streamlit as st

from lib import db, ui
from lib.i18n import lang, t, taxon_name

st.subheader(t("nav_editor"))

# ---- вход ----
if not st.session_state.get("editor_pwd"):
    with st.form("login"):
        st.markdown(f"**{t('login_title')}**")
        pwd = st.text_input(t("password"), type="password")
        who = st.text_input(t("your_name"))
        if st.form_submit_button(t("login")):
            if db.editor_login(pwd):
                st.session_state.editor_pwd = pwd
                st.session_state.editor_name = who
                st.rerun()
            else:
                st.error(t("wrong_pwd"))
    st.stop()

c1, c2 = st.columns([4, 1])
c1.success(f"✏️ {t('logged_in')}: {st.session_state.get('editor_name') or '—'}")
if c2.button(t("logout"), use_container_width=True):
    for k in ("editor_pwd", "editor_name"):
        st.session_state.pop(k, None)
    st.rerun()
PWD, WHO = st.session_state.editor_pwd, st.session_state.get("editor_name")

tab1, tab2, tab3 = st.tabs([t("edit_species_tab"), t("new_species_tab"), t("edit_obs_tab")])

# ---- 1. правка названий и описаний вида ----
with tab1:
    q = st.text_input(t("find_species"), key="ed_q")
    if q:
        found = db.search_taxa(q)
        if found.empty:
            st.info(t("not_found"))
        else:
            opts = {int(r["id"]): f'{taxon_name(r, False) or ""} — {r["name"]}' for _, r in found.iterrows()}
            tid = st.selectbox(t("results"), list(opts), format_func=opts.get, key="ed_sel")
            tx = (db.taxon(tid).get("taxon") or {})
            if st.button(t("wiki_btn"), key="ed_wiki"):
                try:
                    db.fetch_wiki(tid)
                    st.success(t("wiki_done"))
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            with st.form(f"ed_{tid}"):
                a, b = st.columns(2)
                cr = a.text_input(t("common_ru"), tx.get("common_name_ru") or "")
                ck = b.text_input(t("common_kk"), tx.get("common_name_kk") or "")
                dr = a.text_area(t("desc_ru"), tx.get("description_ru") or "", height=220)
                dk = b.text_area(t("desc_kk"), tx.get("description_kk") or "", height=220)
                if st.form_submit_button(t("save")):
                    try:
                        db.write("api_edit_taxon", p_pwd=PWD, p_id=tid, p_common_ru=cr, p_common_kk=ck,
                                 p_desc_ru=dr, p_desc_kk=dk, p_editor=WHO)
                        st.success(t("saved"))
                    except Exception as e:
                        st.error(str(e))
            st.markdown(f"[{t('nav_taxon')} →]({ui.taxon_link(tid)})")

# ---- 2. новый вид / подвид ----
with tab2:
    ranks = {"species": t("r_species"), "subspecies": t("r_subspecies"), "variety": t("r_variety"), "form": t("r_form")}
    with st.form("new_taxon"):
        a, b = st.columns(2)
        latin = a.text_input(t("latin") + " *")
        rank = b.selectbox(t("taxon_rank"), list(ranks), format_func=ranks.get)
        cr = a.text_input(t("common_ru"))
        ck = b.text_input(t("common_kk"))
        fam = a.text_input(t("family"))
        gen = b.text_input(t("genus"))
        parent = st.text_input(t("parent"))
        dr = a.text_area(t("desc_ru"), height=140)
        dk = b.text_area(t("desc_kk"), height=140)
        if st.form_submit_button(t("add_species_btn")):
            try:
                r = db.write("api_add_taxon", p_pwd=PWD, p_name=latin, p_rank=rank, p_common_ru=cr, p_common_kk=ck,
                             p_family=fam, p_genus=gen, p_parent=parent, p_desc_ru=dr, p_desc_kk=dk, p_editor=WHO)
                if r.get("ok"):
                    st.success(f"{t('added')} (id {r.get('id')})")
                else:
                    st.warning(r.get("message"))
            except Exception as e:
                st.error(str(e))

# ---- 3. добавленные наблюдения: правка / удаление ----
with tab3:
    st.page_link("views/add.py", label=t("nav_add"), icon="➕")
    u = db.user_observations(limit=500)
    if u.empty:
        st.info(t("no_data"))
    else:
        labels = {int(r["id"]): f'#{r["id"]} · {(r["name_kk"] if lang() == "kk" else r["name_ru"]) or r["sci"]} · '
                                f'{r.get("author") or ""} · {r.get("observed_on") or ""}' for _, r in u.iterrows()}
        oid = st.selectbox(t("user_obs"), list(labels), format_func=labels.get)
        r = u[u["id"] == oid].iloc[0]
        with st.form(f"uo_{oid}"):
            a, b = st.columns(2)
            tname = a.text_input(t("latin"), r.get("sci") or "")
            sub = b.text_input(t("subspecies"), r.get("subspecies") or "")
            lat = a.number_input(t("lat"), value=float(r["lat"]), format="%.6f")
            lng = b.number_input(t("lng"), value=float(r["lng"]), format="%.6f")
            dr = a.text_area(t("desc_ru"), r.get("description_ru") or "")
            dk = b.text_area(t("desc_kk"), r.get("description_kk") or "")
            auth = a.text_input(t("author"), r.get("author") or "")
            od = b.date_input(t("obs_date"), value=date.fromisoformat(r["observed_on"]) if r.get("observed_on") else date.today())
            s1, s2 = st.columns(2)
            save = s1.form_submit_button(t("save"))
            dele = s2.form_submit_button(t("delete"))
        if save:
            try:
                db.write("api_edit_observation", p_pwd=PWD, p_id=int(oid),
                         p_taxon_id=int(r["taxon_id"]) if pd.notna(r.get("taxon_id")) else None,
                         p_taxon_name=tname, p_subspecies=sub, p_desc_ru=dr, p_desc_kk=dk,
                         p_lat=lat, p_lng=lng, p_observed_on=str(od), p_author=auth)
                st.success(t("saved"))
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if dele:
            try:
                db.write("api_delete_observation", p_pwd=PWD, p_id=int(oid))
                st.success(t("deleted"))
                st.rerun()
            except Exception as e:
                st.error(str(e))
ui.footer()
