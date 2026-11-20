import altair as alt
import pandas as pd
import streamlit as st

from lib import db, ui

MONTHS = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
kind, name = ui.scope()

q = st.text_input("🔎 Найти вид (латынь или русское название)", key="tx_q")
if q:
    found = db.search_taxa(q)
    if found.empty:
        st.info("Не найдено.")
    else:
        opts = {int(r["id"]): f'{r.get("common_name_ru") or ""} — {r["name"]} ({ui.fmt(r.get("n") or 0)} набл.)'
                for _, r in found.iterrows()}
        sel = st.selectbox("Результаты", list(opts), format_func=opts.get)
        st.query_params["id"] = str(sel)

tid = st.query_params.get("id")
if not tid:
    st.info("Выберите вид поиском выше или нажмите на карточку вида на вкладке «Виды».")
    st.stop()

d = db.taxon(int(tid))
t = d.get("taxon") or {}
if not t:
    st.warning("Вид не найден в базе.")
    st.stop()

title = t.get("common_name_ru") or t.get("name")
st.markdown(f"## {ui.esc(title)}")
st.markdown(f"*{ui.esc(t.get('name'))}*" + (f" · {ui.esc(t['common_name_en'])}" if t.get("common_name_en") else ""))

c1, c2 = st.columns([1, 2])
with c1:
    st.image(t.get("photo_url") or ui.PLACEHOLDER, use_container_width=True)
    st.markdown(f"**Семейство:** {t.get('family') or '—'}  \n**Род:** {t.get('genus') or '—'}")
    st.markdown(f"**Наблюдений:** {ui.fmt(d.get('observations'))}  \n**Наблюдателей:** {ui.fmt(d.get('observers'))}")
    links = [f"[iNaturalist ↗]({t.get('inat_url') or ui.INAT + '/taxa/' + str(tid)})"]
    if t.get("wikipedia_url"):
        links.append(f"[Википедия ↗]({t['wikipedia_url']})")
    st.markdown(" · ".join(links))
with c2:
    ui.observations_map("all", "all", taxon=int(tid), mode="points", key="taxon_map", height=430)

m = pd.DataFrame(d.get("months") or [])
a = pd.DataFrame(d.get("areas") or [])
c3, c4 = st.columns(2)
with c3:
    st.markdown("**Сезонность (наблюдения по месяцам)**")
    if not m.empty:
        m = pd.DataFrame({"month": range(1, 13)}).merge(m, how="left").fillna(0)
        m["Месяц"] = m["month"].map(lambda i: MONTHS[int(i) - 1])
        st.altair_chart(alt.Chart(m).mark_bar(color=ui.GREEN).encode(
            x=alt.X("Месяц:N", sort=MONTHS, title=None), y=alt.Y("n:Q", title="Наблюдений"),
            tooltip=["Месяц", alt.Tooltip("n:Q", title="Наблюдений")]), use_container_width=True)
with c4:
    st.markdown("**Где встречается**")
    if not a.empty:
        r = a[a["kind"] == "region"][["name", "n"]].rename(columns={"name": "Область", "n": "Набл."})
        z = a[a["kind"] == "zone"][["name", "n"]].rename(columns={"name": "Природная зона", "n": "Набл."})
        x1, x2 = st.columns(2)
        x1.dataframe(r, hide_index=True, use_container_width=True)
        x2.dataframe(z, hide_index=True, use_container_width=True)

photos = pd.DataFrame(d.get("photos") or [])
if not photos.empty:
    st.markdown("**Фотографии из наблюдений (исследовательский уровень)**")
    cols = st.columns(6)
    for i, (_, p) in enumerate(photos.head(18).iterrows()):
        with cols[i % 6]:
            st.image(p["photo_url"], use_container_width=True)
            st.markdown(f"<span class='muted'>[{p.get('observed_on') or '—'}]({p['uri']}) · {ui.esc(p.get('user_login'))}</span>",
                        unsafe_allow_html=True)

st.markdown("**Все наблюдения вида**")
df, total = db.observations(kind, name, taxon=int(tid), limit=24)
st.caption(f"{ui.fmt(total)} наблюдений · {ui.scope_label(kind, name)}")
ui.observation_cards(df)
ui.footer()
