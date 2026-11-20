from datetime import date

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import lang, t

st.subheader(f"👤 {t('nav_account')}")
a = ui.auth()

# ---------- вход / регистрация ----------
if not a:
    st.info(t("need_account"))
    tab_in, tab_reg = st.tabs([t("tab_login"), t("tab_register")])
    with tab_in:
        with st.form("login_form"):
            lg = st.text_input(t("login_field"))
            pw = st.text_input(t("password"), type="password")
            if st.form_submit_button(t("login"), type="primary"):
                try:
                    st.session_state.auth = db.login(lg, pw)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    with tab_reg:
        with st.form("reg_form"):
            lg = st.text_input(t("login_field"))
            nm = st.text_input(t("display_name"))
            em = st.text_input(t("email_opt"))
            pw = st.text_input(t("password"), type="password")
            pw2 = st.text_input(t("password2"), type="password")
            if st.form_submit_button(t("register_btn"), type="primary"):
                if pw != pw2:
                    st.error(t("pwd_mismatch"))
                else:
                    try:
                        st.session_state.auth = db.register(lg, pw, nm, em)
                        st.success(t("welcome", n=st.session_state.auth["name"]))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
    st.stop()

# ---------- профиль ----------
c1, c2, c3 = st.columns([3, 1.2, 1])
c1.success(t("logged_as", n=f"{a['name']} ({a['login']})") + (" · ✏️ " + a["role"] if ui.is_editor() else ""))
c2.page_link("views/add.py", label=t("btn_add_plant"))
if c3.button(t("logout"), use_container_width=True):
    db.logout(a["token"])
    st.session_state.pop("auth", None)
    st.rerun()

# ---------- мои наблюдения ----------
st.markdown(f"### {t('my_obs')}")
u = db.user_observations(limit=1000)
if not u.empty and "owner" in u:
    mine = u if a.get("role") == "admin" and a.get("login") == "editor" else u[u["owner"] == a["login"]]
else:
    mine = pd.DataFrame()
if mine.empty:
    st.info(t("no_data"))
    st.stop()

labels = {int(r["id"]): f'#{r["id"]} · {(r["name_kk"] if lang() == "kk" else r["name_ru"]) or r["sci"]} · '
                        f'{r.get("observed_on") or ""} · {r.get("region") or ""}' for _, r in mine.iterrows()}
oid = st.selectbox(t("my_obs"), list(labels), format_func=labels.get)
r = mine[mine["id"] == oid].iloc[0]
pc, fc = st.columns([1, 2])
with pc:
    if r.get("has_photo"):
        p = db.user_photo(int(oid))
        if p.get("data"):
            st.image(f"data:{p.get('mime') or 'image/jpeg'};base64,{p['data']}", use_container_width=True)
    import folium
    m = ui.base_map(center=[r["lat"], r["lng"]], zoom=9)
    folium.Marker([r["lat"], r["lng"]], icon=folium.Icon(color="green", icon="leaf")).add_to(m)
    ui.show_map(m, key=f"my_{oid}", height=260)
with fc:
    with st.form(f"my_edit_{oid}"):
        x, y = st.columns(2)
        tname = x.text_input(t("latin"), r.get("sci") or "")
        sub = y.text_input(t("subspecies"), r.get("subspecies") or "")
        lat = x.number_input(t("lat"), value=float(r["lat"]), format="%.6f")
        lng = y.number_input(t("lng"), value=float(r["lng"]), format="%.6f")
        dr = x.text_area(t("desc_ru"), r.get("description_ru") or "")
        dk = y.text_area(t("desc_kk"), r.get("description_kk") or "")
        auth_ = x.text_input(t("author"), r.get("author") or "")
        od = y.date_input(t("obs_date"), value=date.fromisoformat(r["observed_on"]) if r.get("observed_on") else date.today())
        s1, s2 = st.columns(2)
        save = s1.form_submit_button(t("save"))
        dele = s2.form_submit_button(t("delete"))
    if save:
        try:
            db.write("api_edit_observation", p_pwd=a["token"], p_id=int(oid),
                     p_taxon_id=int(r["taxon_id"]) if pd.notna(r.get("taxon_id")) else None,
                     p_taxon_name=tname, p_subspecies=sub, p_desc_ru=dr, p_desc_kk=dk,
                     p_lat=lat, p_lng=lng, p_observed_on=str(od), p_author=auth_)
            st.success(t("saved"))
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if dele:
        try:
            db.write("api_delete_observation", p_pwd=a["token"], p_id=int(oid))
            st.success(t("deleted"))
            st.rerun()
        except Exception as e:
            st.error(str(e))
ui.footer()
