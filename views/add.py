import base64
import io
from datetime import date

import folium
import streamlit as st

from lib import db, recognize, ui
from lib.i18n import lang, t

st.subheader(t("add_title"))
if not ui.auth_token():
    st.info(t("need_account"))
    st.page_link("views/account.py", label=t("btn_login"))
    st.stop()

# ---- 1. точка на карте ----
st.markdown(f"**1. {t('click_map')}**")
pt = st.session_state.get("add_point")
m = ui.base_map(center=pt or ui.KZ_CENTER, zoom=10 if pt else ui.KZ_ZOOM)
ui.add_borders(m, "region")
if pt:
    folium.Marker(pt, icon=folium.Icon(color="green", icon="leaf")).add_to(m)
out = ui.show_map(m, key="add_map", height=480, returned=["last_clicked"])
clicked = (out or {}).get("last_clicked")
if clicked and [round(clicked["lat"], 6), round(clicked["lng"], 6)] != pt:
    st.session_state.add_point = [round(clicked["lat"], 6), round(clicked["lng"], 6)]
    st.rerun()
c1, c2 = st.columns(2)
lat = c1.number_input(t("lat"), value=float(pt[0]) if pt else 0.0, format="%.6f")
lng = c2.number_input(t("lng"), value=float(pt[1]) if pt else 0.0, format="%.6f")

# ---- 2. вид ----
st.markdown(f"**2. {t('nav_taxon')}**")
KK = lang() == "kk"
AV = recognize.available()
for k in ("add_q", "add_free"):                       # результат распознавания подставляем до создания полей
    if k + "_pending" in st.session_state:
        st.session_state[k] = st.session_state.pop(k + "_pending")
if AV["plants"] or AV["animals"]:
    with st.expander("📷 " + ("Суреттен түрді анықтау" if KK else "Распознать вид по фото"), expanded=True):
        r1, r2 = st.columns([2, 1])
        rec_photo = r1.file_uploader("Фото" if not KK else "Сурет", type=["jpg", "jpeg", "png", "webp"], key="rec_photo")
        kinds = {"plant": "🌿 " + ("Өсімдік" if KK else "Растение"), "animal": "🐾 " + ("Жануар" if KK else "Животное")}
        what = r2.radio("Кто на фото?" if not KK else "Суретте кім?",
                        [k for k in kinds if (k == "plant" and AV["plants"]) or AV["animals"]],
                        format_func=kinds.get, key="rec_what")
        if rec_photo:
            r1.image(rec_photo, width=260)
        if r2.button("🔍 " + ("Анықтау" if KK else "Распознать"), disabled=not rec_photo, type="primary", key="rec_go"):
            try:
                with st.spinner("…"):
                    st.session_state["rec_res"] = recognize.identify(rec_photo.getvalue(), what, lat or None,
                                                                      lng or None, lang="ru")
            except Exception as e:
                st.session_state["rec_res"] = []
                st.error(("Анықтау сәтсіз: " if KK else "Не удалось распознать: ") + str(e)[:200])
        res = st.session_state.get("rec_res")
        if res == []:
            st.info("Түр анықталмады — басқа сурет қолданып көріңіз." if KK else
                    "Вид не определён — попробуйте другое, более чёткое фото.")
        for i, x in enumerate(res or []):
            if not x.get("latin"):
                continue
            rbm = [r for r in (db.safe("api_rb_list", [], p_q=x["latin"], p_kingdom=x["kingdom"]) or [])
                   if (r.get("latin") or "").lower() == x["latin"].lower()]
            c_a, c_b = st.columns([4, 1])
            line = f"**{x['score'] * 100:.0f}%** · *{x['latin']}*" + (f" — {x['common']}" if x.get("common") else "") \
                   + (f" · {x['family']}" if x.get("family") else "")
            if rbm:
                line += " · 🔴 " + ("Қызыл кітапта" if KK else "в Красной книге") + f" ({rbm[0].get('category') or '—'})"
            c_a.markdown(line)
            if c_b.button("✔ " + ("Таңдау" if KK else "Выбрать"), key=f"rec_pick_{i}"):
                found = db.search_taxa(x["latin"])
                if not found.empty and x["kingdom"] == "plantae":
                    st.session_state["add_q_pending"] = x["latin"]
                else:
                    st.session_state["add_free_pending"] = x["latin"]
                st.rerun()
        st.caption(("Анықтау нәтижесі — ұсыныс қана; түрді өзіңіз тексеріңіз." if KK else
                    "Результат распознавания — подсказка; проверьте вид сами.")
                   + (" Pl@ntNet" if AV["plants"] else "") + (" · CV" if AV["animals"] else ""))
q = st.text_input(t("find_species"), key="add_q")
taxon_id = None
if q:
    found = db.search_taxa(q)
    if not found.empty:
        opts = {0: "—"}
        for _, r in found.iterrows():
            cn = (r.get("common_name_kk") or r.get("common_name_ru")) if lang() == "kk" else r.get("common_name_ru")
            opts[int(r["id"])] = f'{cn or ""} — {r["name"]}'
        taxon_id = st.selectbox(t("species_choose"), list(opts), format_func=opts.get) or None
taxon_name_free = st.text_input(t("species_other"), disabled=bool(taxon_id), key="add_free")
sub = st.text_input(t("subspecies"))

# ---- 3. описание, фото ----
st.markdown(f"**3. {t('description')} / {t('photo')}**")
d1, d2 = st.columns(2)
desc_ru = d1.text_area(t("desc_ru"), height=120)
desc_kk = d2.text_area(t("desc_kk"), height=120)
a1, a2 = st.columns(2)
author = a1.text_input(t("author"), value=ui.auth().get("name") or "")
obs_date = a2.date_input(t("obs_date"), value=date.today(), format="DD.MM.YYYY")
photo = st.file_uploader(t("upload_photo"), type=["jpg", "jpeg", "png", "webp"])
if not photo and st.session_state.get("rec_photo"):
    photo = st.session_state["rec_photo"]          # фото, по которому распознавали, станет фото наблюдения
    st.caption("📷 " + ("Анықтау үшін жүктелген сурет қолданылады" if lang() == "kk" else "Будет использовано фото из распознавания"))
if photo:
    st.image(photo, width=300)

if st.button(t("add_btn"), type="primary"):
    if not (lat or lng):
        st.error(t("need_point"))
    elif not taxon_id and not taxon_name_free.strip():
        st.error(t("need_taxon"))
    else:
        b64 = mime = None
        if photo:
            try:  # уменьшаем фото до 1600 px, чтобы не раздувать базу
                from PIL import Image
                photo.seek(0)
                img = Image.open(photo).convert("RGB")
                img.thumbnail((1600, 1600))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                b64, mime = base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
            except Exception:
                b64, mime = base64.b64encode(photo.getvalue()).decode(), photo.type
        try:
            r = db.write("api_add_observation", p_pwd=ui.auth_token(), p_taxon_id=taxon_id,
                         p_taxon_name=taxon_name_free, p_subspecies=sub, p_desc_ru=desc_ru, p_desc_kk=desc_kk,
                         p_lat=lat, p_lng=lng, p_observed_on=str(obs_date), p_author=author,
                         p_photo_b64=b64, p_photo_mime=mime)
            st.success(f"{t('added')} #{r.get('id')}")
            st.session_state.pop("add_point", None)
        except Exception as e:
            st.error(str(e))

st.markdown("---")
st.page_link("views/account.py", label=t("my_obs"), icon="📋")
ui.footer()
