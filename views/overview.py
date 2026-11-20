import altair as alt
import pandas as pd
import streamlit as st

from lib import db, ui

kind, name = ui.scope()
s = ui.header()
if ui.empty_db_notice(s):
    st.stop()

# ---- Последние наблюдения ----
c1, c2 = st.columns([5, 1])
c1.subheader("Последние наблюдения")
c2.page_link("views/observations.py", label="Посмотреть все →")
recent, _ = db.observations(kind, name, limit=12)
ui.observation_cards(recent.head(12))
st.write("")

# ---- Три лидерборда ----
b1, b2, b3 = st.columns(3)
obs_top, _ = db.observers(kind, name, "observations", 6)
sp_top, _ = db.observers(kind, name, "species", 6)
taxa_top, _ = db.species(kind, name, "", 6)
with b1:
    ui.board("Больше всего наблюдений",
             [(r.get("icon"), r["user_login"], f"{ui.INAT}/people/{r['user_login']}", ui.fmt(r["observations"]))
              for _, r in obs_top.iterrows()])
    st.page_link("views/observers.py", label="Посмотреть все")
with b2:
    ui.board("Больше всего видов",
             [(r.get("icon"), r["user_login"], f"{ui.INAT}/people/{r['user_login']}", ui.fmt(r["species"]))
              for _, r in sp_top.iterrows()])
    st.page_link("views/observers.py", label="Посмотреть все")
with b3:
    ui.board("Чаще всего наблюдают",
             [(r.get("photo_url"), r.get("common_name_ru") or r.get("name"), ui.taxon_link(r["taxon_id"]),
               ui.fmt(r["n"])) for _, r in taxa_top.iterrows()], square=True)
    st.page_link("views/species.py", label="Посмотреть все")
st.write("")

# ---- Требования / Статистика ----
r1, r2 = st.columns(2)
with r1:
    st.subheader("Требования проекта")
    st.markdown(
        "Наблюдения в этом проекте должны соответствовать условиям:\n\n"
        "| | |\n|---|---|\n"
        "| 🌿 Таксон | Растения (Plantae) |\n"
        "| 📍 Местоположение | Казахстан |\n"
        "| 👤 Пользователи | Любой |\n"
        "| ✅ Уровень качества | Исследовательский, Требуется идентификация |\n"
        "| 📅 Дата | Любая |")
with r2:
    st.subheader("Статистика")
    q = pd.DataFrame({"Уровень": list(ui.QUALITY.values()),
                      "n": [s.get("research", 0), s.get("needs_id", 0), s.get("casual", 0)]})
    q = q[q["n"] > 0]
    chart = alt.Chart(q).mark_arc(innerRadius=70).encode(
        theta="n:Q",
        color=alt.Color("Уровень:N", scale=alt.Scale(domain=list(ui.QUALITY.values()),
                                                      range=[ui.GREEN, "#f4e48b", "#aaaaaa"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Уровень", alt.Tooltip("n:Q", title="Наблюдений", format=",")])
    st.altair_chart(chart, use_container_width=True)
    st.page_link("views/stats.py", label="Подробная статистика →")

# ---- Карта наблюдений ----
st.subheader("Карта наблюдений")
m = st.radio("Вид карты", ["Сетка", "Теплокарта", "Точки"], horizontal=True, label_visibility="collapsed")
ui.observations_map(kind, name, mode={"Сетка": "grid", "Теплокарта": "heat", "Точки": "points"}[m],
                    key="overview_map")
ui.footer()
