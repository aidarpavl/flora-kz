import math

import pandas as pd
import streamlit as st

from lib import db, ui

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader("Наблюдения")
f1, f2, f3, f4 = st.columns([3, 2, 2, 3])
q = f1.text_input("Вид или таксон (лат./рус.)", key="ob_q", placeholder="например, Tulipa или тюльпан")
quality_label = f2.selectbox("Уровень качества", ["Любой"] + list(ui.QUALITY.values()), key="ob_qual")
quality = {v: k for k, v in ui.QUALITY.items()}.get(quality_label)
user = f3.text_input("Наблюдатель (логин)", key="ob_user").strip() or None
dates = f4.date_input("Период наблюдения", value=(), key="ob_dates", format="DD.MM.YYYY")
d_from = dates[0] if len(dates) > 0 else None
d_to = dates[1] if len(dates) > 1 else None

taxon_id = None
if q:
    found = db.search_taxa(q)
    if not found.empty:
        opts = {0: f"Все таксоны по запросу «{q}»"}
        opts.update({int(r["id"]): f'{r.get("common_name_ru") or ""} {r["name"]}'.strip() for _, r in found.iterrows()})
        taxon_id = st.selectbox("Уточнить вид", list(opts), format_func=opts.get, key="ob_taxon") or None

view = st.radio("Вид", ["🗺️ Карта", "🖼️ Сетка", "📋 Таблица"], horizontal=True, index=1, key="ob_view",
                label_visibility="collapsed")

if view == "🗺️ Карта":
    if q and not taxon_id:
        st.caption("На карте показываются наблюдения выбранного вида — уточните вид в списке выше.")
    ui.observations_map(kind, name, taxon=taxon_id, user=user, quality=quality, mode="points",
                        key="obs_map", borders="region" if kind != "zone" else "zone")
else:
    PAGE = 48 if view == "🖼️ Сетка" else 100
    key = f"ob_page::{kind}:{name}:{q}:{taxon_id}:{quality}:{user}:{d_from}:{d_to}:{view}"
    page = st.session_state.get(key, 1)
    df, total = db.observations(kind, name, taxon=taxon_id, user=user, quality=quality,
                                q=None if taxon_id else q, date_from=d_from, date_to=d_to,
                                limit=PAGE, offset=(page - 1) * PAGE)
    pages = max(1, math.ceil(total / PAGE))
    st.markdown(f"**{ui.fmt(total)}**{'+' if total >= 100000 else ''} наблюдений · страница {page} из {ui.fmt(pages)}")
    if view == "🖼️ Сетка":
        ui.observation_cards(df)
    elif not df.empty:
        t = pd.DataFrame({
            "Фото": df["photo_url"],
            "Название": [ui.taxon_title(r)[0] for _, r in df.iterrows()],
            "Научное": df["obs_taxon_name"],
            "Наблюдатель": df["user_login"],
            "Дата": df["observed_on"],
            "Место": df["place_guess"],
            "Область": df["region"],
            "Зона": df["zone"],
            "Качество": df["quality_grade"].map(ui.QUALITY),
            "Ссылка": df["uri"],
        })
        st.dataframe(t, hide_index=True, use_container_width=True, height=600,
                     column_config={"Фото": st.column_config.ImageColumn(width="small"),
                                    "Ссылка": st.column_config.LinkColumn(display_text="iNat ↗")})
    n1, n2, n3 = st.columns([1, 2, 1])
    if n1.button("← Назад", disabled=page <= 1, use_container_width=True):
        st.session_state[key] = page - 1
        st.rerun()
    if n3.button("Вперёд →", disabled=page >= pages, use_container_width=True):
        st.session_state[key] = page + 1
        st.rerun()
ui.footer()
