import altair as alt
import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import t, taxon_name

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

c1, c2 = st.columns([5, 1])
c1.subheader(t("recent"))
c2.page_link("views/observations.py", label=t("see_all"))
recent, _ = db.observations(kind, name, limit=12)
ui.observation_cards(recent)
st.write("")

b1, b2, b3 = st.columns(3)
obs_top, _ = db.observers(kind, name, "observations", 6)
sp_top, _ = db.observers(kind, name, "species", 6)
taxa_top, _ = db.species(kind, name, "", 6)
with b1:
    ui.board(t("most_obs"), [(r.get("icon"), r["user_login"], "",
                              ui.fmt(r["observations"])) for _, r in obs_top.iterrows()])
    st.page_link("views/observers.py", label=t("see_all"))
with b2:
    ui.board(t("most_species"), [(r.get("icon"), r["user_login"], "",
                                  ui.fmt(r["species"])) for _, r in sp_top.iterrows()])
    st.page_link("views/observers.py", label=t("see_all"))
with b3:
    ui.board(t("most_observed"), [(r.get("photo_url"), taxon_name(r), ui.taxon_link(r["taxon_id"]), ui.fmt(r["n"]))
                                  for _, r in taxa_top.iterrows()], square=True)
    st.page_link("views/species.py", label=t("see_all"))
st.write("")

r1, r2 = st.columns(2)
with r1:
    st.subheader(t("requirements"))
    st.markdown(t("req_text"))
with r2:
    st.subheader(t("stats"))
    ql = ui.quality_labels()
    q = pd.DataFrame({"label": list(ql.values()), "n": [s.get("research", 0), s.get("needs_id", 0), s.get("casual", 0)]})
    st.altair_chart(alt.Chart(q[q["n"] > 0]).mark_arc(innerRadius=70).encode(
        theta="n:Q",
        color=alt.Color("label:N", scale=alt.Scale(domain=list(ql.values()), range=[ui.GREEN, "#f4e48b", "#aaaaaa"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[alt.Tooltip("label:N", title=t("quality")), alt.Tooltip("n:Q", title=t("nav_observations"), format=",")]),
        use_container_width=True)
    st.page_link("views/stats.py", label=t("more_stats"))

st.subheader(t("obs_map"))
m = st.radio("map", [t("map_points"), t("map_heat")], horizontal=True, label_visibility="collapsed")
ui.observations_map(kind, name, mode="heat" if m == t("map_heat") else "points", key="overview_map")
ui.footer()
