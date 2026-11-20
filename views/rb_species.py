"""Страница вида из Красной книги: обзор, карта, редактирование (для редакторов)."""
import json
from datetime import date

import pandas as pd
import streamlit as st
from folium.plugins import Draw

from lib import db, rb, ui
from lib.i18n import t

KK = rb.kk()


def L(ru, kz):
    return kz if KK else ru


A = ui.auth_token()
st.markdown(f'<a href="./redbook" target="_self">← 🌺 {ui.esc(t("rb_title"))}</a>', unsafe_allow_html=True)

# ---------- выбор вида ----------
sid = st.query_params.get("id")
if not sid:
    allrows = pd.DataFrame(db.safe("api_rb_list", []) or [])
    if allrows.empty:
        st.info(t("rb_empty"))
        st.stop()
    opts = {int(r["id"]): f'{rb.nm(r)} — {r["latin"]}' for _, r in allrows.iterrows()}
    pick = st.selectbox(t("rb_choose"), list(opts), format_func=opts.get, index=None)
    if pick is None:
        st.stop()
    st.query_params["id"] = str(pick)
    st.rerun()
sid = int(sid)

d = db.safe("api_rb_get", {}, p_id=sid, p_auth=A) or {}
s = d.get("species") or {}
if not s:
    st.warning(t("not_found"))
    st.stop()
can = bool(A) and bool((db.safe("api_rb_can_edit", {}, p_auth=A, p_id=sid) or {}).get("can"))
points, ranges = d.get("points", []), d.get("ranges", [])

# ---------- заголовок ----------
st.markdown(f"## {ui.esc(rb.nm(s))}")
other = s.get("name_ru") if KK else s.get("name_kk")
st.markdown(f"*{ui.esc(s.get('latin'))}*" + (f" · {ui.esc(other)}" if other else "")
            + f' &nbsp; <span style="padding:2px 10px;border-radius:10px;background:{rb.cat_color(s.get("category"))};'
              f'color:#fff;font-size:.85rem">{ui.esc(rb.cat_label(s.get("category")))}</span>', unsafe_allow_html=True)

tabs = [L("📋 Обзор", "📋 Шолу"), L("🗺️ Карта находок", "🗺️ Табылған жерлер картасы")]
if can:
    tabs.append(L("✏️ Редактировать", "✏️ Өңдеу"))
elif not A:
    st.caption(L("Редакторы могут исправлять и дополнять эту страницу — войдите в аккаунт.",
                 "Редакторлар бұл бетті түзетіп, толықтыра алады — аккаунтқа кіріңіз."))
T = st.tabs(tabs)


def points_for_map():
    return [{"lat": p["lat"], "lng": p["lng"], "category": s.get("category"),
             "title": f"{rb.nm(s)} · {p.get('observed_on') or ''} {rb.txt(p, 'note')}"} for p in points]


def ranges_for_map():
    return [{**g, "category": s.get("category"), "latin": s.get("latin"), "name_ru": s.get("name_ru"),
             "name_kk": s.get("name_kk")} for g in ranges]


# ======================= ОБЗОР =======================
with T[0]:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(rb.card_img(s), use_container_width=True)
        if s.get("photo_attr") and not s.get("has_photo"):
            st.caption("📷 " + s["photo_attr"])
        rank = {"species": t("r_species"), "subspecies": t("r_subspecies"), "variety": t("r_variety"),
                "form": t("r_form")}.get(s.get("rank"), s.get("rank"))
        st.markdown(f"**{t('family')}:** {rb.fam(s)}  \n**{t('genus')}:** *{s.get('genus') or '—'}*  \n"
                    f"**{L('Вид', 'Түр')}:** *{s.get('latin')}*  \n**{t('taxon_rank')}:** {rank}"
                    + (f"  \n**{t('parent')}:** *{s['parent_latin']}*" if s.get("parent_latin") else "")
                    + f"  \n**{t('rb_category')}:** {rb.cat_label(s.get('category'))}"
                    + f"  \n**{L('Точек находок', 'Табылған нүктелер')}:** {ui.fmt(len(points))}"
                    + (f" · ⬟ {len(ranges)}" if ranges else ""))
        links = []
        wiki = (s.get("wiki_kk_url") or s.get("wiki_ru_url")) if KK else s.get("wiki_ru_url")
        if wiki:
            links.append(f"[Wikipedia ↗]({wiki})")
        if s.get("gbif_key"):
            links.append(f"[GBIF ↗](https://www.gbif.org/species/{s['gbif_key']})")
        if s.get("taxon_id"):
            links.append(f"[iNaturalist →]({ui.taxon_link(s['taxon_id'])})")
        st.markdown(" · ".join(links))
    with c2:
        m = ui.base_map()
        ui.add_borders(m, "region")
        rb.add_layers(m, points_for_map(), ranges_for_map())
        ui.show_map(m, key=f"rbs_map_{sid}", height=440)
        st.caption(t("rb_precise") if d.get("precise") else t("rb_rounded"))
    for title, base in ((t("description"), "description"), (t("rb_habitat"), "habitat"), (t("rb_protection"), "protection")):
        text = rb.txt(s, base)
        if text:
            st.markdown(f"#### {title}")
            st.markdown(f'<div class="desc">{ui.esc(text).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
    if not rb.txt(s, "description"):
        st.info(t("no_description"))
    st.caption(f"{t('author')}: {s.get('author') or '—'} · {L('обновлено', 'жаңартылды')} {str(s.get('updated_at') or '')[:10]}")

# ======================= КАРТА =======================
with T[1]:
    m = ui.base_map()
    ui.add_borders(m, "region")
    rb.add_layers(m, points_for_map(), ranges_for_map())
    ui.show_map(m, key=f"rbs_bigmap_{sid}", height=620)
    if points:
        df = pd.DataFrame(points)
        df["note"] = [rb.txt(p, "note") for p in points]
        st.dataframe(df[["lat", "lng", "observed_on", "region", "zone", "note"]].rename(columns={
            "lat": L("Широта", "Ендік"), "lng": L("Долгота", "Бойлық"), "observed_on": L("Дата", "Күні"),
            "region": L("Область", "Облыс"), "zone": L("Природная зона", "Табиғи аймақ"), "note": L("Источник", "Дереккөз")}),
            use_container_width=True, hide_index=True)

# ======================= РЕДАКТИРОВАНИЕ =======================
if can:
    with T[2]:
        P = f"rbe_{sid}_"
        FIELDS = ["latin", "rank", "name_ru", "name_kk", "parent_latin", "genus", "family", "family_ru", "family_kk",
                  "category", "description_ru", "description_kk", "habitat_ru", "habitat_kk", "protection_ru",
                  "protection_kk", "wiki_ru_url", "wiki_kk_url", "photo_url", "photo_attr"]
        if not st.session_state.get(P + "init"):
            for f in FIELDS:
                st.session_state[P + f] = s.get(f) or ""
            st.session_state[P + "rank"] = s.get("rank") or "species"
            st.session_state[P + "init"] = True
        for f, v in (st.session_state.pop(P + "pending", None) or {}).items():   # из Википедии / перевода
            st.session_state[P + f] = v or ""
        for msg in st.session_state.pop(P + "msg", []):
            getattr(st, msg[0])(msg[1])

        st.markdown(f"##### 1. {L('Названия и систематика', 'Атаулары және жүйелеу')}")
        a, b, c = st.columns(3)
        a.text_input(t("latin") + " *", key=P + "latin")
        ranks = {"species": t("r_species"), "subspecies": t("r_subspecies"), "variety": t("r_variety"), "form": t("r_form")}
        b.selectbox(t("taxon_rank"), list(ranks), format_func=ranks.get, key=P + "rank")
        c.selectbox(t("rb_category"), [""] + list(rb.CATS), key=P + "category",
                    format_func=lambda x: rb.cat_label(x) if x else "—")
        a.text_input(t("common_ru"), key=P + "name_ru")
        b.text_input(t("common_kk"), key=P + "name_kk")
        c.text_input(t("parent"), key=P + "parent_latin")
        a.text_input(t("genus") + " (лат.)", key=P + "genus")
        b.text_input(t("family") + " (лат.)", key=P + "family")
        c.write("")
        a.text_input(L("Семейство (рус.)", "Тұқымдас (орыс.)"), key=P + "family_ru")
        b.text_input(L("Семейство (каз.)", "Тұқымдас (қаз.)"), key=P + "family_kk")

        st.markdown(f"##### 2. {L('Описание', 'Сипаттама')}")
        st.caption(L("Загрузите текст из Википедии или вставьте свой (Ctrl+V). Перед сохранением текст можно поправить.",
                     "Мәтінді Уикипедиядан жүктеңіз немесе өзіңіз қойыңыз (Ctrl+V). Сақтау алдында түзетуге болады."))
        w1, w2, w3, w4 = st.columns([3, 2, 1.4, 1.4])
        wtitle = w1.text_input(L("Статья Википедии (название или ссылка, можно пусто)",
                                 "Уикипедия мақаласы (атауы немесе сілтеме, бос болуы мүмкін)"), key=P + "wtitle")
        w2.write("")
        if w2.button("📖 " + L("Загрузить из Википедии", "Уикипедиядан жүктеу"), key=P + "wbtn", use_container_width=True):
            try:
                r = db.write("api_rb_wiki_fetch", p_auth=A, p_id=sid, p_title=wtitle or None)
                if r.get("ok"):
                    pend = {"description_ru": r.get("ru") or st.session_state[P + "description_ru"],
                            "description_kk": r.get("kk") or st.session_state[P + "description_kk"],
                            "wiki_ru_url": r.get("ru_url") or st.session_state[P + "wiki_ru_url"],
                            "wiki_kk_url": r.get("kk_url") or st.session_state[P + "wiki_kk_url"]}
                    if r.get("thumb") and not st.session_state[P + "photo_url"] and not s.get("has_photo"):
                        pend["photo_url"], pend["photo_attr"] = r["thumb"], "Wikipedia / Wikimedia Commons"
                    st.session_state[P + "pending"] = pend
                    note = L("Казахский текст — из казахской Википедии.", "Қазақша мәтін — қазақ Уикипедиясынан.") \
                        if r.get("kk_native") else L("Казахский текст — машинный перевод, проверьте его.",
                                                     "Қазақша мәтін — машиналық аударма, тексеріңіз.")
                    st.session_state[P + "msg"] = [("success", L("Текст загружен в поля ниже. ", "Мәтін төмендегі өрістерге жүктелді. ")
                                                     + note + L(" Нажмите «Сохранить».", " «Сақтау» басыңыз."))]
                    st.rerun()
                else:
                    st.warning(r.get("message") or t("wiki_none"))
            except Exception as e:
                st.error(str(e))
        w3.write("")
        if w3.button("рус → қаз", key=P + "tr1", use_container_width=True, help=L("Перевести описание, места обитания и меры охраны на казахский",
                                                                               "Сипаттаманы қазақшаға аудару")):
            pend = {}
            for base in ("description", "habitat", "protection"):
                src = st.session_state[P + base + "_ru"]
                if src:
                    r = db.write("api_rb_translate", p_auth=A, p_text=src, p_sl="ru", p_tl="kk")
                    if r.get("text"):
                        pend[base + "_kk"] = r["text"]
            st.session_state[P + "pending"] = pend
            st.session_state[P + "msg"] = [("info", L("Перевод вставлен — проверьте и сохраните.", "Аударма қойылды — тексеріп, сақтаңыз."))]
            st.rerun()
        w4.write("")
        if w4.button("қаз → рус", key=P + "tr2", use_container_width=True):
            pend = {}
            for base in ("description", "habitat", "protection"):
                src = st.session_state[P + base + "_kk"]
                if src:
                    r = db.write("api_rb_translate", p_auth=A, p_text=src, p_sl="kk", p_tl="ru")
                    if r.get("text"):
                        pend[base + "_ru"] = r["text"]
            st.session_state[P + "pending"] = pend
            st.session_state[P + "msg"] = [("info", L("Перевод вставлен — проверьте и сохраните.", "Аударма қойылды — тексеріп, сақтаңыз."))]
            st.rerun()
        a, b = st.columns(2)
        a.text_area(t("desc_ru"), key=P + "description_ru", height=280)
        b.text_area(t("desc_kk"), key=P + "description_kk", height=280)
        a.text_area(t("rb_habitat_ru"), key=P + "habitat_ru", height=110)
        b.text_area(t("rb_habitat_kk"), key=P + "habitat_kk", height=110)
        a.text_area(t("rb_protect_ru"), key=P + "protection_ru", height=110)
        b.text_area(t("rb_protect_kk"), key=P + "protection_kk", height=110)
        a.text_input("Wikipedia (рус.) URL", key=P + "wiki_ru_url")
        b.text_input("Wikipedia (қаз.) URL", key=P + "wiki_kk_url")

        st.markdown(f"##### 3. {L('Фото', 'Сурет')}")
        f1, f2 = st.columns([1, 2])
        f1.image(rb.card_img(s), use_container_width=True)
        upload = f2.file_uploader(L("Загрузить своё фото (заменит текущее)", "Өз суретіңізді жүктеу (қазіргіні ауыстырады)"),
                                  type=["jpg", "jpeg", "png", "webp"], key=P + "upload")
        f2.text_input(L("…или ссылка на фото (https://…)", "…немесе суретке сілтеме (https://…)"), key=P + "photo_url")
        f2.text_input(L("Автор / источник фото", "Сурет авторы / дереккөзі"), key=P + "photo_attr")
        remove = f2.checkbox(L("Убрать загруженное фото (показывать фото по ссылке)",
                               "Жүктелген суретті алып тастау (сілтемедегі сурет көрсетіледі)"),
                             key=P + "remove", disabled=not s.get("has_photo"))

        if st.button("💾 " + L("Сохранить изменения", "Өзгерістерді сақтау"), type="primary", key=P + "save"):
            fields = {f: st.session_state[P + f] for f in FIELDS}
            fields["remove_photo"] = bool(remove)
            b64, mime = rb.to_b64(upload)
            try:
                db.write("api_rb_save_ext", p_auth=A, p_id=sid, p_fields=fields, p_photo_b64=b64, p_photo_mime=mime)
                st.session_state[P + "init"] = False
                st.session_state[P + "msg"] = [("success", t("saved"))]
                st.rerun()
            except Exception as e:
                st.error(str(e))

        # ---- 4. точки и ареалы ----
        st.markdown(f"##### 4. {t('rb_objects')}")
        st.caption(t("rb_draw_hint"))
        m = ui.base_map()
        ui.add_borders(m, "region")
        rb.add_layers(m, [{"lat": p["lat"], "lng": p["lng"], "category": s.get("category"), "title": f"#{p['id']}"}
                          for p in points], ranges_for_map())
        Draw(export=False, position="topleft",
             draw_options={"polyline": False, "circle": False, "circlemarker": False,
                           "marker": True, "polygon": True, "rectangle": True},
             edit_options={"edit": False}).add_to(m)
        out = ui.show_map(m, key=f"rbe_draw_{sid}", height=520, returned=["all_drawings"])
        drawings = (out or {}).get("all_drawings") or []
        new_pts = [g for g in drawings if (g.get("geometry") or {}).get("type") == "Point"]
        new_rng = [g for g in drawings if (g.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]
        st.caption(t("rb_drawn", p=len(new_pts), r=len(new_rng)))
        with st.expander(L("➕ Добавить точку по координатам", "➕ Координаттар бойынша нүкте қосу")):
            k1, k2 = st.columns(2)
            mlat = k1.number_input(L("Широта", "Ендік"), 40.0, 56.0, 43.25, step=0.0001, format="%.5f", key=P + "mlat")
            mlng = k2.number_input(L("Долгота", "Бойлық"), 46.0, 88.0, 76.95, step=0.0001, format="%.5f", key=P + "mlng")
            use_manual = st.checkbox(L("Добавить эту точку при сохранении", "Сақтағанда осы нүктені қосу"), key=P + "useman")
        n1, n2, n3 = st.columns([2, 2, 1])
        note_ru = n1.text_input(t("rb_note_ru"), key=P + "nru")
        note_kk = n2.text_input(t("rb_note_kk"), key=P + "nkk")
        pdate = n3.date_input(t("obs_date"), value=date.today(), key=P + "pd", format="DD.MM.YYYY")
        if st.button(t("rb_save_drawings"), type="primary", disabled=not (drawings or use_manual), key=P + "sd"):
            ok, errs = 0, []
            coords = [g["geometry"]["coordinates"][:2] for g in new_pts] + ([[mlng, mlat]] if use_manual else [])
            for lng, lat in coords:
                try:
                    db.write("api_rb_add_point", p_auth=A, p_species=sid, p_lat=lat, p_lng=lng,
                             p_note_ru=note_ru, p_note_kk=note_kk, p_date=str(pdate))
                    ok += 1
                except Exception as e:
                    errs.append(str(e))
            for g in new_rng:
                try:
                    db.write("api_rb_add_range", p_auth=A, p_species=sid, p_geojson=json.dumps(g["geometry"]),
                             p_note_ru=note_ru, p_note_kk=note_kk)
                    ok += 1
                except Exception as e:
                    errs.append(str(e))
            for e in errs:
                st.error(e)
            if ok:
                st.session_state[P + "msg"] = [("success", f"{t('saved')}: {ok}")]
                st.rerun()

        with st.expander(t("delete") + " — " + t("rb_objects")):
            popts = {p["id"]: f"📍 #{p['id']} · {p['lat']}, {p['lng']} · {p.get('region') or ''} · {rb.txt(p, 'note')}"
                     for p in points}
            sel = st.multiselect(L("Точки", "Нүктелер"), list(popts), format_func=popts.get, key=P + "delpts")
            if st.button(L("Удалить выбранные точки", "Таңдалған нүктелерді жою"), disabled=not sel, key=P + "delpbtn"):
                r = db.write("api_rb_delete_points", p_auth=A, p_species=sid, p_ids=sel)
                st.session_state[P + "msg"] = [("success", f"{t('deleted')}: {r.get('deleted')}")]
                st.rerun()
            for g in ranges:
                if st.button(f"🗑️ ⬟ #{g['id']} · {ui.fmt(g.get('area_km2'))} км²", key=P + f"delr{g['id']}"):
                    db.write("api_rb_delete", p_auth=A, p_what="range", p_id=int(g["id"]))
                    st.rerun()
ui.footer()
