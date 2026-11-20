from datetime import date

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import lang, t, taxon_name

st.subheader(t("nav_editor"))
a = ui.auth()

# ---- вход: аккаунт с ролью редактора или пароль редактора (администратор) ----
if not a:
    st.info(t("need_account"))
    st.page_link("views/account.py", label=t("btn_login"))
if not ui.is_editor():
    if a:
        st.warning(t("editors_only"))
    with st.expander(t("admin_login"), expanded=not a):
        with st.form("admin_login"):
            pwd = st.text_input(t("password"), type="password")
            if st.form_submit_button(t("login")):
                if db.editor_login(pwd):
                    st.session_state.auth = {"token": pwd, "login": "editor", "name": "Редактор", "role": "admin"}
                    st.rerun()
                else:
                    st.error(t("wrong_pwd"))
    st.stop()

AUTH = a["token"]
WHO = a["name"]
is_admin = a.get("login") == "editor"
st.success(t("logged_as", n=WHO) + " · ✏️")

tabs = [t("edit_species_tab"), t("new_species_tab"), t("edit_obs_tab")] + ([t("users_tab")] if is_admin else [])
tab = st.tabs(tabs)

# ---- 1. правка названий и описаний вида ----
with tab[0]:
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
                    w = db.fetch_wiki(tid, AUTH)
                    if w.get("message") and w["message"] != "ok":
                        st.warning(w["message"])
                    else:
                        st.success(t("wiki_done"))
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
            with st.form(f"ed_{tid}"):
                c1, c2 = st.columns(2)
                cr = c1.text_input(t("common_ru"), tx.get("common_name_ru") or "")
                ck = c2.text_input(t("common_kk"), tx.get("common_name_kk") or "")
                dr = c1.text_area(t("desc_ru"), tx.get("description_ru") or "", height=220)
                dk = c2.text_area(t("desc_kk"), tx.get("description_kk") or "", height=220)
                if st.form_submit_button(t("save")):
                    try:
                        db.write("api_edit_taxon", p_pwd=AUTH, p_id=tid, p_common_ru=cr, p_common_kk=ck,
                                 p_desc_ru=dr, p_desc_kk=dk, p_editor=WHO)
                        st.success(t("saved"))
                    except Exception as e:
                        st.error(str(e))
            st.markdown(f"[{t('nav_taxon')} →]({ui.taxon_link(tid)})")

# ---- 2. новый вид / подвид ----
with tab[1]:
    ranks = {"species": t("r_species"), "subspecies": t("r_subspecies"), "variety": t("r_variety"), "form": t("r_form")}
    with st.form("new_taxon"):
        c1, c2 = st.columns(2)
        latin = c1.text_input(t("latin") + " *")
        rank = c2.selectbox(t("taxon_rank"), list(ranks), format_func=ranks.get)
        cr = c1.text_input(t("common_ru"))
        ck = c2.text_input(t("common_kk"))
        fam = c1.text_input(t("family"))
        gen = c2.text_input(t("genus"))
        parent = st.text_input(t("parent"))
        dr = c1.text_area(t("desc_ru"), height=140)
        dk = c2.text_area(t("desc_kk"), height=140)
        if st.form_submit_button(t("add_species_btn")):
            try:
                r = db.write("api_add_taxon", p_pwd=AUTH, p_name=latin, p_rank=rank, p_common_ru=cr, p_common_kk=ck,
                             p_family=fam, p_genus=gen, p_parent=parent, p_desc_ru=dr, p_desc_kk=dk, p_editor=WHO)
                st.success(f"{t('added')} (id {r.get('id')})") if r.get("ok") else st.warning(r.get("message"))
            except Exception as e:
                st.error(str(e))

# ---- 3. все добавленные наблюдения ----
with tab[2]:
    u = db.user_observations(limit=1000)
    if u.empty:
        st.info(t("no_data"))
    else:
        labels = {int(r["id"]): f'#{r["id"]} · {(r["name_kk"] if lang() == "kk" else r["name_ru"]) or r["sci"]} · '
                                f'{r.get("owner") or r.get("author") or ""} · {r.get("observed_on") or ""}'
                  for _, r in u.iterrows()}
        oid = st.selectbox(t("user_obs"), list(labels), format_func=labels.get)
        r = u[u["id"] == oid].iloc[0]
        with st.form(f"uo_{oid}"):
            c1, c2 = st.columns(2)
            tname = c1.text_input(t("latin"), r.get("sci") or "")
            sub = c2.text_input(t("subspecies"), r.get("subspecies") or "")
            lat = c1.number_input(t("lat"), value=float(r["lat"]), format="%.6f")
            lng = c2.number_input(t("lng"), value=float(r["lng"]), format="%.6f")
            dr = c1.text_area(t("desc_ru"), r.get("description_ru") or "")
            dk = c2.text_area(t("desc_kk"), r.get("description_kk") or "")
            auth_ = c1.text_input(t("author"), r.get("author") or "")
            od = c2.date_input(t("obs_date"), value=date.fromisoformat(r["observed_on"]) if r.get("observed_on") else date.today())
            s1, s2 = st.columns(2)
            save = s1.form_submit_button(t("save"))
            dele = s2.form_submit_button(t("delete"))
        if save or dele:
            try:
                if save:
                    db.write("api_edit_observation", p_pwd=AUTH, p_id=int(oid),
                             p_taxon_id=int(r["taxon_id"]) if pd.notna(r.get("taxon_id")) else None,
                             p_taxon_name=tname, p_subspecies=sub, p_desc_ru=dr, p_desc_kk=dk,
                             p_lat=lat, p_lng=lng, p_observed_on=str(od), p_author=auth_)
                    st.success(t("saved"))
                else:
                    db.write("api_delete_observation", p_pwd=AUTH, p_id=int(oid))
                    st.success(t("deleted"))
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ---- 4. пользователи (только администратор) ----
if is_admin:
    with tab[3]:
        try:
            users = pd.DataFrame(db.write("api_users", p_pwd=AUTH))
        except Exception as e:
            users = pd.DataFrame()
            st.error(str(e))
        if not users.empty:
            st.dataframe(users, hide_index=True, use_container_width=True)
            with st.form("role"):
                c1, c2 = st.columns(2)
                who = c1.selectbox(t("login_field"), users["login"].tolist())
                role = c2.selectbox(t("role"), ["user", "editor"])
                if st.form_submit_button(t("set_role")):
                    try:
                        db.write("api_set_role", p_pwd=AUTH, p_login=who, p_role=role)
                        st.success(t("saved"))
                    except Exception as e:
                        st.error(str(e))
ui.footer()
