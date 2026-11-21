"""Страница вида из Красной книги: обзор, карта и редактирование прямо на странице (по коду редактора)."""
import json
from datetime import date

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw

from lib import db, rb, ui
from lib.i18n import t

KK = rb.kk()


def L(ru, kz):
    return kz if KK else ru


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

A = ui.auth_token()
d = db.safe("api_rb_get", {}, p_id=sid, p_auth=A) or {}
s = d.get("species") or {}
if not s:
    st.warning(t("not_found"))
    st.stop()
can = bool(A) and bool((db.safe("api_rb_can_edit", {}, p_auth=A, p_id=sid) or {}).get("can"))
points, ranges = d.get("points", []), d.get("ranges", [])
P = f"rbe_{sid}_"
EDIT = st.session_state.get("rb_edit_mode", False)

# ---------- заголовок + кнопка «Редактировать» справа от названия ----------
h1, h2 = st.columns([5, 1.5], vertical_alignment="center")
other = s.get("name_ru") if KK else s.get("name_kk")
h1.markdown(f"## {ui.esc(rb.nm(s))}")
h1.markdown(f"*{ui.esc(s.get('latin'))}*" + (f" · {ui.esc(other)}" if other else "")
            + f' &nbsp; <span style="padding:2px 10px;border-radius:10px;background:{rb.cat_color(s.get("category"))};'
              f'color:#fff;font-size:.85rem">{ui.esc(rb.cat_label(s.get("category")))}</span>', unsafe_allow_html=True)
if not EDIT:
    if h2.button("✏️ " + L("Редактировать", "Өңдеу"), type="primary", use_container_width=True, key="rb_edit_on"):
        st.session_state["rb_edit_mode"] = True
        st.rerun()
else:
    if h2.button("✖ " + L("Закрыть редактор", "Өңдеуді жабу"), use_container_width=True, key="rb_edit_off"):
        st.session_state["rb_edit_mode"] = False
        for k in [k for k in st.session_state if k.startswith(P)]:
            del st.session_state[k]
        st.rerun()


def points_for_map():
    return [{"lat": p["lat"], "lng": p["lng"], "category": s.get("category"),
             "title": f"{rb.nm(s)} · {p.get('observed_on') or ''} {rb.txt(p, 'note')}"} for p in points]


def ranges_for_map():
    return [{**g, "category": s.get("category"), "latin": s.get("latin"), "name_ru": s.get("name_ru"),
             "name_kk": s.get("name_kk")} for g in ranges]


# ======================= ВХОД ПО КОДУ РЕДАКТОРА =======================
if EDIT and not can:
    st.info(L("Введите код редактора, чтобы изменять фото, описание и точки на карте.",
              "Фото, сипаттама мен картадағы нүктелерді өзгерту үшін редактор кодын енгізіңіз."))
    with st.form("rb_code_form"):
        code = st.text_input(L("Код редактора", "Редактор коды"), type="password")
        ok = st.form_submit_button(L("Войти", "Кіру"), type="primary")
    if ok:
        try:   # код редактора → обычная сессия на 30 дней (сохраняется в cookie, действует на всех страницах)
            st.session_state.auth = db.write("api_editor_session", p_pwd=code)
            st.rerun()
        except Exception:
            st.error(t("wrong_pwd"))
    st.caption(L("Можно также войти через «Войти / Регистрация» аккаунтом с ролью редактора.",
                 "«Кіру / Тіркелу» арқылы редактор рөлі бар аккаунтпен де кіруге болады."))
    st.stop()

# ======================= ПРОСМОТР =======================
if not EDIT:
    T = st.tabs([L("📋 Обзор", "📋 Шолу"), L("🗺️ Карта находок", "🗺️ Табылған жерлер картасы")])
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
                links.append(f"[{L('Наблюдения вида', 'Түрдің бақылаулары')} →]({ui.taxon_link(s['taxon_id'])})")
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
    ui.footer()
    st.stop()

# ======================= РЕДАКТИРОВАНИЕ НА СТРАНИЦЕ =======================
FIELDS = ["latin", "rank", "name_ru", "name_kk", "parent_latin", "genus", "family", "family_ru", "family_kk",
          "category", "description_ru", "description_kk", "habitat_ru", "habitat_kk", "protection_ru",
          "protection_kk", "wiki_ru_url", "wiki_kk_url", "photo_url", "photo_attr"]
PT_COLS = ["lat", "lng", "observed_on", "note_ru", "note_kk"]
if not st.session_state.get(P + "init"):
    for f in FIELDS:
        st.session_state[P + f] = s.get(f) or ""
    st.session_state[P + "rank"] = s.get("rank") or "species"
    st.session_state[P + "pts_df"] = pd.DataFrame(
        [{c: (p.get(c) if p.get(c) is not None else "") for c in PT_COLS} for p in points], columns=PT_COLS)
    st.session_state[P + "new_pts"] = []
    st.session_state[P + "init"] = True
for f, v in (st.session_state.pop(P + "pending", None) or {}).items():   # из Википедии / перевода
    st.session_state[P + f] = v or ""
for msg in st.session_state.pop(P + "msg", []):
    getattr(st, msg[0])(msg[1])
st.success(L("Режим редактирования. Измените нужное и нажмите «💾 Сохранить» внизу страницы — прежние данные будут заменены.",
             "Өңдеу режимі. Қажеттісін өзгертіп, беттің төменгі жағындағы «💾 Сақтау» батырмасын басыңыз."))

# ---- 1. фото ----
st.markdown(f"#### 🖼️ {L('Фото растения', 'Өсімдік суреті')}")
f1, f2 = st.columns([1, 2])
upload = f2.file_uploader(L("Выбрать фото с компьютера (заменит текущее)", "Компьютерден сурет таңдау (қазіргіні ауыстырады)"),
                          type=["jpg", "jpeg", "png", "webp"], key=P + "upload")
if upload:
    f1.image(upload, use_container_width=True, caption=L("Новое фото (ещё не сохранено)", "Жаңа сурет (әлі сақталмаған)"))
else:
    f1.image(rb.card_img(s), use_container_width=True)
f2.text_input(L("…или ссылка на фото (https://…)", "…немесе суретке сілтеме (https://…)"), key=P + "photo_url")
f2.text_input(L("Автор / источник фото", "Сурет авторы / дереккөзі"), key=P + "photo_attr")
remove = f2.checkbox(L("Убрать загруженное раньше фото (показывать фото по ссылке)",
                       "Бұрын жүктелген суретті алып тастау (сілтемедегі сурет көрсетіледі)"),
                     key=P + "remove", disabled=not s.get("has_photo"))

# ---- 2. точки на карте ----
st.markdown(f"#### 📍 {L('Точки на карте', 'Картадағы нүктелер')}")
pencil = st.toggle("✏️ " + L("Карандаш: щёлкайте по карте, чтобы добавить точки", "Қарындаш: нүкте қосу үшін картаны басыңыз"),
                   key=P + "pencil")
new_pts = st.session_state[P + "new_pts"]
m = ui.base_map()
ui.add_borders(m, "region")
rb.add_layers(m, [{"lat": p["lat"], "lng": p["lng"], "category": s.get("category"), "title": f"#{p['id']}"} for p in points],
              ranges_for_map())
for i, p in enumerate(new_pts, 1):
    folium.Marker([p["lat"], p["lng"]], tooltip=L(f"Новая точка {i}", f"Жаңа нүкте {i}"),
                  icon=folium.Icon(color="red", icon="pencil", prefix="fa")).add_to(m)
Draw(export=False, position="topleft",
     draw_options={"polyline": False, "circle": False, "circlemarker": False, "marker": False,
                   "polygon": True, "rectangle": True},
     edit_options={"edit": False}).add_to(m)
out = ui.show_map(m, key=f"rbe_map_{sid}", height=520, returned=["last_clicked", "all_drawings"]) or {}
click = out.get("last_clicked")
if pencil and click and st.session_state.get(P + "last_click") != click:
    st.session_state[P + "last_click"] = click
    new_pts.append({"lat": round(click["lat"], 5), "lng": round(click["lng"], 5)})
    st.rerun()
elif click:
    st.session_state[P + "last_click"] = click
new_rng = [g for g in (out.get("all_drawings") or []) if (g.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]
st.caption(L(f"Новых точек: {len(new_pts)} · нарисовано ареалов: {len(new_rng)}. "
             "Ареал (многоугольник) рисуется кнопками слева на карте.",
             f"Жаңа нүктелер: {len(new_pts)} · сызылған ареалдар: {len(new_rng)}."))
if new_pts and st.button("↩️ " + L("Убрать последнюю новую точку", "Соңғы жаңа нүктені алып тастау"), key=P + "undo"):
    new_pts.pop()
    st.rerun()

st.markdown(L("**Все точки вида** — координаты можно исправить прямо в таблице, строку можно удалить "
              "(выделите слева и нажмите 🗑) или добавить (＋ внизу таблицы).",
              "**Түрдің барлық нүктелері** — координаттарды кестеде түзетуге, жолды жоюға немесе қосуға болады."))
edited = st.data_editor(
    st.session_state[P + "pts_df"], num_rows="dynamic", use_container_width=True, key=P + "pts_editor",
    column_config={
        "lat": st.column_config.NumberColumn(L("Широта", "Ендік"), min_value=35.0, max_value=60.0, format="%.5f", required=True),
        "lng": st.column_config.NumberColumn(L("Долгота", "Бойлық"), min_value=40.0, max_value=95.0, format="%.5f", required=True),
        "observed_on": st.column_config.TextColumn(L("Дата (ГГГГ-ММ-ДД)", "Күні (ЖЖЖЖ-АА-КК)")),
        "note_ru": st.column_config.TextColumn(L("Примечание (рус.)", "Ескерту (орыс.)")),
        "note_kk": st.column_config.TextColumn(L("Примечание (каз.)", "Ескерту (қаз.)")),
    })

# ---- 3. описание ----
st.markdown(f"#### 📝 {L('Описание', 'Сипаттама')}")
st.caption(L("Загрузите текст из Википедии или вставьте свой (Ctrl+V).",
             "Мәтінді Уикипедиядан жүктеңіз немесе өзіңіз қойыңыз (Ctrl+V)."))
w1, w2, w3, w4 = st.columns([3, 2, 1.4, 1.4], vertical_alignment="bottom")
wtitle = w1.text_input(L("Статья Википедии (название или ссылка, можно пусто)",
                         "Уикипедия мақаласы (атауы немесе сілтеме, бос болуы мүмкін)"), key=P + "wtitle")
if w2.button("📖 " + L("Из Википедии", "Уикипедиядан"), key=P + "wbtn", use_container_width=True):
    try:
        r = db.write("api_rb_wiki_fetch", p_auth=A, p_id=sid, p_title=wtitle or None)
        if r.get("ok"):
            st.session_state[P + "pending"] = {
                "description_ru": r.get("ru") or st.session_state[P + "description_ru"],
                "description_kk": r.get("kk") or st.session_state[P + "description_kk"],
                "wiki_ru_url": r.get("ru_url") or st.session_state[P + "wiki_ru_url"],
                "wiki_kk_url": r.get("kk_url") or st.session_state[P + "wiki_kk_url"]}
            st.session_state[P + "msg"] = [("info", L("Текст из Википедии вставлен в поля — проверьте и сохраните.",
                                                      "Уикипедия мәтіні қойылды — тексеріп, сақтаңыз."))]
            st.rerun()
        else:
            st.warning(r.get("message") or t("wiki_none"))
    except Exception as e:
        st.error(str(e))
for col, (sl, tl), label in ((w3, ("ru", "kk"), "рус → қаз"), (w4, ("kk", "ru"), "қаз → рус")):
    if col.button(label, key=P + f"tr_{sl}", use_container_width=True):
        pend = {}
        for base in ("description", "habitat", "protection"):
            src = st.session_state[P + f"{base}_{sl}"]
            if src:
                r = db.write("api_rb_translate", p_auth=A, p_text=src, p_sl=sl, p_tl=tl)
                if r.get("text"):
                    pend[f"{base}_{tl}"] = r["text"]
        st.session_state[P + "pending"] = pend
        st.session_state[P + "msg"] = [("info", L("Перевод вставлен — проверьте и сохраните.", "Аударма қойылды — тексеріп, сақтаңыз."))]
        st.rerun()
a, b = st.columns(2)
a.text_area(t("desc_ru"), key=P + "description_ru", height=260)
b.text_area(t("desc_kk"), key=P + "description_kk", height=260)
a.text_area(t("rb_habitat_ru"), key=P + "habitat_ru", height=100)
b.text_area(t("rb_habitat_kk"), key=P + "habitat_kk", height=100)
a.text_area(t("rb_protect_ru"), key=P + "protection_ru", height=100)
b.text_area(t("rb_protect_kk"), key=P + "protection_kk", height=100)

# ---- 4. названия и систематика ----
with st.expander("🏷️ " + L("Названия, систематика, категория", "Атаулары, жүйелеу, санат")):
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
    c.text_input("Wikipedia (рус.) URL", key=P + "wiki_ru_url")
    a.text_input(L("Семейство (рус.)", "Тұқымдас (орыс.)"), key=P + "family_ru")
    b.text_input(L("Семейство (каз.)", "Тұқымдас (қаз.)"), key=P + "family_kk")
    c.text_input("Wikipedia (қаз.) URL", key=P + "wiki_kk_url")
    if ranges:
        st.markdown(L("**Ареалы:**", "**Ареалдар:**"))
        for g in ranges:
            if st.button(f"🗑️ ⬟ #{g['id']} · {ui.fmt(g.get('area_km2'))} км²", key=P + f"delr{g['id']}"):
                db.write("api_rb_delete", p_auth=A, p_what="range", p_id=int(g["id"]))
                st.rerun()

# ---- СОХРАНИТЬ ----
st.markdown("---")
if st.button("💾 " + L("Сохранить", "Сақтау"), type="primary", use_container_width=True, key=P + "save"):
    errs = []
    fields = {f: st.session_state[P + f] for f in FIELDS}
    fields["remove_photo"] = bool(remove)
    if upload:
        upload.seek(0)   # файл уже читался для предпросмотра
    b64, mime = rb.to_b64(upload)
    try:
        db.write("api_rb_save_ext", p_auth=A, p_id=sid, p_fields=fields, p_photo_b64=b64, p_photo_mime=mime)
    except Exception as e:
        errs.append(str(e))
    rows = []
    for _, r in pd.DataFrame(edited).iterrows():
        try:
            lat, lng = float(r["lat"]), float(r["lng"])
        except (TypeError, ValueError):
            continue
        if pd.isna(lat) or pd.isna(lng):
            continue
        cl = lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)  # noqa: E731
        rows.append({"lat": lat, "lng": lng, "observed_on": cl(r.get("observed_on"))[:10],
                     "note_ru": cl(r.get("note_ru")), "note_kk": cl(r.get("note_kk"))})
    today = str(date.today())
    rows += [{"lat": p["lat"], "lng": p["lng"], "observed_on": today, "note_ru": "", "note_kk": ""} for p in new_pts]
    try:
        r = db.write("api_rb_replace_points", p_auth=A, p_species=sid, p_points=rows)
        n_pts = r.get("points")
    except Exception as e:
        errs.append(str(e))
        n_pts = None
    for g in new_rng:
        try:
            db.write("api_rb_add_range", p_auth=A, p_species=sid, p_geojson=json.dumps(g["geometry"]),
                     p_note_ru="", p_note_kk="")
        except Exception as e:
            errs.append(str(e))
    if errs:
        for e in errs:
            st.error(e)
    else:
        for k in [k for k in st.session_state if k.startswith(P)]:
            del st.session_state[k]
        st.session_state[P + "msg"] = [("success", L(f"Сохранено в базе: фото, описание и {n_pts} точек.",
                                                     f"Дерекқорға сақталды: сурет, сипаттама және {n_pts} нүкте."))]
        st.rerun()
ui.footer()
