import streamlit as st

from lib import db, ui

ui.hero("Флора Казахстана",
        "Растения Казахстана по наблюдениям iNaturalist — по всей стране, областям и природным зонам")

s = db.project_stats()
ui.stats_row([("Наблюдений", int(s["observations"] or 0)), ("Видов", int(s["species"] or 0)),
              ("Наблюдателей", int(s["observers"] or 0)), ("Последнее наблюдение", s.get("last_observed"))])

if not s["observations"]:
    st.warning("База пока пустая. Запустите загрузку данных: `python etl/load_inat.py` (см. README).")
    st.stop()

st.write("")
left, right = st.columns([3, 2])
with left:
    st.subheader("Число видов по природным зонам")
    ui.choropleth("zone", height=430)
with right:
    st.subheader("Природные зоны")
    z = db.area_stats("zone")
    if not z.empty:
        st.dataframe(z[["name", "species", "observations"]].rename(
            columns={"name": "Зона", "species": "Видов", "observations": "Наблюдений"}),
            hide_index=True, use_container_width=True)
    st.page_link("views/map.py", label="Открыть карту областей и зон →", icon="🗺️")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Крупнейшие семейства")
    f = db.family_stats(15)
    if not f.empty:
        st.bar_chart(f.set_index("family")["species"], horizontal=True, color=ui.GREEN,
                     x_label="Видов", y_label="")
with c2:
    st.subheader("Топ наблюдателей")
    o = db.observer_stats(15)
    if not o.empty:
        o["Профиль"] = "https://www.inaturalist.org/people/" + o["user_login"]
        st.dataframe(o.rename(columns={"user_login": "Наблюдатель", "observations": "Наблюдений",
                                       "species": "Видов"}),
                     hide_index=True, use_container_width=True,
                     column_config={"Профиль": st.column_config.LinkColumn(display_text="iNat")})

st.subheader("Самые наблюдаемые виды")
top, _ = db.species_list("all", None, "", 12, 0)
cols = st.columns(6)
for i, (_, r) in enumerate(top.iterrows()):
    cols[i % 6].markdown(ui.species_card(r), unsafe_allow_html=True)

ui.footer()
