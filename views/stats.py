import altair as alt
import pandas as pd
import streamlit as st

from lib import db, ui

MONTHS = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

st.subheader(f"Статистика · {ui.scope_label(kind, name)}")
m = db.months(kind, name)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Наблюдения по годам**")
    if not m.empty:
        y = m[m["year"] > 0].groupby("year", as_index=False)["observations"].sum()
        st.altair_chart(alt.Chart(y).mark_bar(color=ui.GREEN).encode(
            x=alt.X("year:O", title="Год"), y=alt.Y("observations:Q", title="Наблюдений"),
            tooltip=[alt.Tooltip("year:O", title="Год"), alt.Tooltip("observations:Q", title="Наблюдений", format=",")]),
            use_container_width=True)
with c2:
    st.markdown("**Сезонность (по месяцам)**")
    if not m.empty:
        mm = m[m["month"] > 0].groupby("month", as_index=False)["observations"].sum()
        mm["Месяц"] = mm["month"].map(lambda i: MONTHS[i - 1])
        st.altair_chart(alt.Chart(mm).mark_bar(color="#8fbf3f").encode(
            x=alt.X("Месяц:N", sort=MONTHS, title=None), y=alt.Y("observations:Q", title="Наблюдений"),
            tooltip=["Месяц", alt.Tooltip("observations:Q", title="Наблюдений", format=",")]),
            use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown("**Уровни качества**")
    q = pd.DataFrame({"Уровень": list(ui.QUALITY.values()),
                      "n": [s.get("research", 0), s.get("needs_id", 0), s.get("casual", 0)]})
    st.altair_chart(alt.Chart(q[q["n"] > 0]).mark_arc(innerRadius=60).encode(
        theta="n:Q",
        color=alt.Color("Уровень:N", scale=alt.Scale(domain=list(ui.QUALITY.values()),
                                                      range=[ui.GREEN, "#f4e48b", "#aaaaaa"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Уровень", alt.Tooltip("n:Q", title="Наблюдений", format=",")]), use_container_width=True)
with c4:
    st.markdown("**Крупнейшие семейства (по числу видов)**")
    f = db.families(kind, name, 20)
    if not f.empty:
        st.altair_chart(alt.Chart(f).mark_bar(color=ui.GREEN).encode(
            y=alt.Y("family:N", sort="-x", title=None), x=alt.X("species:Q", title="Видов"),
            tooltip=[alt.Tooltip("family:N", title="Семейство"), alt.Tooltip("species:Q", title="Видов"),
                     alt.Tooltip("observations:Q", title="Наблюдений", format=",")]),
            use_container_width=True)

if not m.empty:
    st.markdown("**Наблюдения по месяцам (динамика)**")
    t = m[m["year"] > 0].copy()
    t["Дата"] = pd.to_datetime(dict(year=t["year"], month=t["month"].clip(lower=1), day=1))
    st.altair_chart(alt.Chart(t).mark_area(color=ui.GREEN, opacity=.6, line=True).encode(
        x=alt.X("Дата:T", title=None), y=alt.Y("observations:Q", title="Наблюдений"),
        tooltip=[alt.Tooltip("Дата:T", format="%m.%Y"), alt.Tooltip("observations:Q", title="Наблюдений")]),
        use_container_width=True)

st.markdown("**Сравнение территорий**")
k = st.radio("Территории", ["Области", "Природные зоны"], horizontal=True, label_visibility="collapsed")
a = pd.DataFrame(db.areas("region" if k == "Области" else "zone"))
if not a.empty:
    st.altair_chart(alt.Chart(a).mark_bar(color=ui.GREEN).encode(
        y=alt.Y("name:N", sort="-x", title=None), x=alt.X("species:Q", title="Видов"),
        tooltip=[alt.Tooltip("name:N", title="Территория"), alt.Tooltip("species:Q", title="Видов"),
                 alt.Tooltip("observations:Q", title="Наблюдений", format=","),
                 alt.Tooltip("observers:Q", title="Наблюдателей")]), use_container_width=True)
ui.footer()
