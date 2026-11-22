"""Эксперты сайта: рейтинг участников, которые определяют виды, и лента наблюдений для определения."""
import math

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import lang, t

KK = lang() == "kk"


def L(ru, kz):
    return kz if KK else ru


kind, name = ui.scope()
s = ui.header()

st.subheader(t("identifiers_title"))
st.caption(L("Эксперты — участники сайта, которые определяют виды в наблюдениях других участников. "
             "Список начат заново: учитываются только определения, сделанные на этом сайте.",
             "Сарапшылар — басқа қатысушылардың бақылауларындағы түрлерді анықтайтын сайт қатысушылары. "
             "Тізім жаңадан басталды: тек осы сайтта жасалған анықтамалар есептеледі."))
tab_top, tab_id = st.tabs([L("🏆 Рейтинг экспертов", "🏆 Сарапшылар рейтингі"), L("🔍 Определить вид", "🔍 Түрді анықтау")])

# ======================= РЕЙТИНГ =======================
with tab_top:
    PAGE = 100
    key = f"id_page::{kind}:{name}"
    page = st.session_state.get(key, 1)
    df, total = db.identifiers(kind, name, PAGE, (page - 1) * PAGE)
    if df.empty:
        st.info(L("Пока нет экспертов. Станьте первым: откройте вкладку «🔍 Определить вид».",
                  "Әзірге сарапшылар жоқ. Бірінші болыңыз: «🔍 Түрді анықтау» қойындысын ашыңыз."))
    else:
        tb = pd.DataFrame({
            t("rank"): range((page - 1) * PAGE + 1, (page - 1) * PAGE + 1 + len(df)),
            t("nav_identifiers"): df["user_login"],
            t("identifications"): df["identifications"],
            L("Видов", "Түрлер"): df.get("species", 0),
        })
        st.dataframe(tb, hide_index=True, use_container_width=True, height=min(700, 60 + 36 * len(tb)), column_config={
            t("identifications"): st.column_config.ProgressColumn(format="%d", min_value=0,
                                                                  max_value=int(df["identifications"].max()))})
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

# ======================= ОПРЕДЕЛИТЬ ВИД =======================
with tab_id:
    A = ui.auth_token()
    if not A:
        st.info(L("Определять виды могут зарегистрированные участники сайта — войдите или зарегистрируйтесь.",
                  "Түрлерді сайтқа тіркелген қатысушылар анықтай алады — кіріңіз немесе тіркеліңіз."))
        st.page_link("views/account.py", label=t("btn_login"))
    only_new = st.toggle(L("Только ещё не определённые", "Тек әлі анықталмағандар"), key="iq_new")
    QP = 24
    qkey = f"iq_page::{kind}:{name}:{only_new}"
    qpage = st.session_state.get(qkey, 1)
    q = db.safe("api_ident_queue", {"total": 0, "rows": []}, p_auth=A or None, p_limit=QP, p_offset=(qpage - 1) * QP,
                p_kind=kind, p_name=name, p_only_new=only_new) or {}
    rows = q.get("rows") or []
    if not rows:
        st.info(L("Наблюдений участников пока нет.", "Қатысушылардың бақылаулары әзірге жоқ."))
    for r in rows:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if r.get("has_photo"):
                    p = db.user_photo(int(r["id"]))
                    if p.get("data"):
                        st.image(f"data:{p.get('mime') or 'image/jpeg'};base64,{p['data']}", use_container_width=True)
                else:
                    st.image(ui.PLACEHOLDER, use_container_width=True)
            with c2:
                loc = (r.get("name_kk") or r.get("name_ru")) if KK else r.get("name_ru")
                st.markdown(f"**#{r['id']} · {ui.esc(loc or '')}** *{ui.esc(r.get('sci') or '—')}*"
                            + (f" {ui.esc(r['subspecies'])}" if r.get("subspecies") else ""))
                st.caption(f"👤 {r.get('owner') or '—'} · 📅 {r.get('observed_on') or '—'} · "
                           f"📍 {ui.area_name({'name': r.get('region')}) if r.get('region') else '—'}")
                ids = r.get("ids") or []
                if ids:
                    st.markdown("\n".join(f"- **{ui.esc(i['who'])}**: *{ui.esc(i['taxon'])}*"
                                          + (f" — {ui.esc(i['comment'])}" if i.get("comment") else "")
                                          + f" ({i.get('at') or ''})" for i in ids))
                else:
                    st.caption(L("Ещё никто не определял.", "Әлі ешкім анықтамаған."))
                if A and not r.get("mine"):
                    fk = f"iq_{r['id']}"
                    with st.expander(("✏️ " + L("Изменить моё определение", "Анықтамамды өзгерту")) if r.get("my_taxon")
                                     else ("🔍 " + L("Определить вид", "Түрді анықтау"))):
                        qq = st.text_input(L("Поиск вида (латынь, русское или казахское название)",
                                             "Түрді іздеу (латынша, орысша не қазақша)"), key=fk + "_q",
                                           value=r.get("my_taxon") or "")
                        tid, tname = None, qq.strip()
                        if qq.strip():
                            found = db.search_taxa(qq.strip())
                            if not found.empty:
                                opts = {0: L(f"Как написано: {qq.strip()}", f"Жазылғандай: {qq.strip()}")}
                                for _, f in found.iterrows():
                                    cn = (f.get("common_name_kk") or f.get("common_name_ru")) if KK else f.get("common_name_ru")
                                    opts[int(f["id"])] = f'{f["name"]}' + (f" — {cn}" if isinstance(cn, str) and cn else "")
                                tid = st.selectbox(L("Выберите вид", "Түрді таңдаңыз"), list(opts), format_func=opts.get,
                                                   key=fk + "_sel", index=1 if len(opts) > 1 else 0) or None
                                if tid:
                                    tname = str(found[found["id"] == tid].iloc[0]["name"])
                        com = st.text_input(L("Комментарий (необязательно)", "Түсініктеме (міндетті емес)"), key=fk + "_c")
                        b1, b2 = st.columns(2)
                        if b1.button("💾 " + L("Сохранить определение", "Анықтаманы сақтау"), key=fk + "_s",
                                     type="primary", disabled=not tname, use_container_width=True):
                            try:
                                db.write("api_identify", p_auth=A, p_obs=int(r["id"]), p_taxon_id=tid,
                                         p_taxon_name=tname, p_comment=com or None)
                                st.success(L("Сохранено", "Сақталды"))
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                        if r.get("my_taxon") and b2.button("🗑️ " + L("Убрать моё определение", "Анықтамамды алып тастау"),
                                                           key=fk + "_d", use_container_width=True):
                            try:
                                db.write("api_identify_delete", p_auth=A, p_obs=int(r["id"]))
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                elif A and r.get("mine"):
                    st.caption(L("Это ваше наблюдение.", "Бұл сіздің бақылауыңыз."))
    qtotal = int(q.get("total") or 0)
    qpages = max(1, math.ceil(qtotal / QP))
    if qpages > 1:
        n1, n2, n3 = st.columns([1, 2, 1])
        n2.markdown(f"<div style='text-align:center'>{t('total', n=ui.fmt(qtotal), p=qpage, pp=qpages)}</div>",
                    unsafe_allow_html=True)
        if n1.button(t("prev"), disabled=qpage <= 1, use_container_width=True, key="iq_prev"):
            st.session_state[qkey] = qpage - 1
            st.rerun()
        if n3.button(t("next"), disabled=qpage >= qpages, use_container_width=True, key="iq_next"):
            st.session_state[qkey] = qpage + 1
            st.rerun()
ui.footer()
