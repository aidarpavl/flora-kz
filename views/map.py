import streamlit as st

from lib import db, ui

ui.hero("Карта", "Разнообразие флоры по областям, природным зонам и по всему Казахстану")

mode = st.radio("Разделение карты", ["Области", "Природные зоны", "Весь Казахстан"], horizontal=True)

if mode == "Весь Казахстан":
    show_pts = st.toggle("Показать точки наблюдений (последние 5000)", value=True)
    pts = db.observations(limit=5000) if show_pts else None
    ui.choropleth("region", points=pts)
    s = db.project_stats()
    ui.stats_row([("Наблюдений", int(s["observations"] or 0)), ("Видов", int(s["species"] or 0)),
                  ("Наблюдателей", int(s["observers"] or 0))])
    kind, name = "all", None
else:
    kind = "region" if mode == "Области" else "zone"
    stats = db.area_stats(kind)
    if stats.empty:
        st.info("Данных нет — запустите ETL.")
        st.stop()
    c1, c2 = st.columns([1, 2])
    with c1:
        name = st.selectbox("Подсветить территорию", ["—"] + stats["name"].tolist())
        name = None if name == "—" else name
        show_pts = st.toggle("Точки наблюдений", value=bool(name))
    pts = db.observations(kind=kind, name=name, limit=5000) if (show_pts and name) else None
    ui.choropleth(kind, highlight=name, points=pts)
    st.caption("Цвет — число видов: светлее = меньше, темнее = больше. Наведите курсор на территорию.")

    st.subheader("Области" if kind == "region" else "Природные зоны")
    st.dataframe(stats[["name", "species", "observations", "observers"]].rename(columns={
        "name": "Территория", "species": "Видов", "observations": "Наблюдений", "observers": "Наблюдателей"}),
        hide_index=True, use_container_width=True,
        column_config={"Видов": st.column_config.ProgressColumn(
            format="%d", min_value=0, max_value=int(stats["species"].max()))})

title = "Весь Казахстан" if kind == "all" else (name or "")
if kind == "all" or name:
    st.subheader(f"Топ-24 вида: {title}")
    top, total = db.species_list(kind, name, "", 24, 0)
    st.caption(f"Всего видов: {total}")
    cols = st.columns(6)
    for i, (_, r) in enumerate(top.iterrows()):
        cols[i % 6].markdown(ui.species_card(r), unsafe_allow_html=True)

ui.footer()
