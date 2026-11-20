import altair as alt
import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import area_name, months, t

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

MONTHS = months()
OBS = t("observations_n").capitalize()
st.subheader(f"{t('stats')} · {ui.scope_label(kind, name)}")
m = db.months(kind, name)
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**{t('by_years')}**")
    if not m.empty:
        y = m[m["year"] > 0].groupby("year", as_index=False)["observations"].sum()
        st.altair_chart(alt.Chart(y).mark_bar(color=ui.GREEN).encode(
            x=alt.X("year:O", title=t("year")), y=alt.Y("observations:Q", title=OBS),
            tooltip=[alt.Tooltip("year:O", title=t("year")), alt.Tooltip("observations:Q", title=OBS, format=",")]),
            use_container_width=True)
with c2:
    st.markdown(f"**{t('seasonality')}**")
    if not m.empty:
        mm = m[m["month"] > 0].groupby("month", as_index=False)["observations"].sum()
        mm["m"] = mm["month"].map(lambda i: MONTHS[i - 1])
        st.altair_chart(alt.Chart(mm).mark_bar(color="#8fbf3f").encode(
            x=alt.X("m:N", sort=MONTHS, title=None), y=alt.Y("observations:Q", title=OBS),
            tooltip=[alt.Tooltip("m:N", title=t("month")), alt.Tooltip("observations:Q", title=OBS, format=",")]),
            use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown(f"**{t('quality')}**")
    ql = ui.quality_labels()
    q = pd.DataFrame({"label": list(ql.values()), "n": [s.get("research", 0), s.get("needs_id", 0), s.get("casual", 0)]})
    st.altair_chart(alt.Chart(q[q["n"] > 0]).mark_arc(innerRadius=60).encode(
        theta="n:Q",
        color=alt.Color("label:N", scale=alt.Scale(domain=list(ql.values()), range=[ui.GREEN, "#f4e48b", "#aaaaaa"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[alt.Tooltip("label:N", title=t("quality")), alt.Tooltip("n:Q", title=OBS, format=",")]),
        use_container_width=True)
with c4:
    st.markdown(f"**{t('families')}**")
    f = db.families(kind, name, 20)
    if not f.empty:
        st.altair_chart(alt.Chart(f).mark_bar(color=ui.GREEN).encode(
            y=alt.Y("family:N", sort="-x", title=None), x=alt.X("species:Q", title=t("c_species")),
            tooltip=[alt.Tooltip("family:N", title=t("family")), alt.Tooltip("species:Q", title=t("c_species")),
                     alt.Tooltip("observations:Q", title=OBS, format=",")]), use_container_width=True)

if not m.empty:
    st.markdown(f"**{t('dynamics')}**")
    d = m[m["year"] > 0].copy()
    d["d"] = pd.to_datetime(dict(year=d["year"], month=d["month"].clip(lower=1), day=1))
    st.altair_chart(alt.Chart(d).mark_area(color=ui.GREEN, opacity=.6, line=True).encode(
        x=alt.X("d:T", title=None), y=alt.Y("observations:Q", title=OBS),
        tooltip=[alt.Tooltip("d:T", format="%m.%Y", title=t("date")), alt.Tooltip("observations:Q", title=OBS)]),
        use_container_width=True)

st.markdown(f"**{t('compare')}**")
k = st.radio("cmp", [t("regions"), t("zones")], horizontal=True, label_visibility="collapsed")
items = db.areas("region" if k == t("regions") else "zone")
if items:
    a = pd.DataFrame([{**x, "title": area_name(x)} for x in items])
    st.altair_chart(alt.Chart(a).mark_bar(color=ui.GREEN).encode(
        y=alt.Y("title:N", sort="-x", title=None), x=alt.X("species:Q", title=t("c_species")),
        tooltip=[alt.Tooltip("title:N", title=t("territory")), alt.Tooltip("species:Q", title=t("c_species")),
                 alt.Tooltip("observations:Q", title=OBS, format=","),
                 alt.Tooltip("observers:Q", title=t("observers_n"))]), use_container_width=True)
ui.footer()
