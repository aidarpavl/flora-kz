import streamlit as st

from lib import db, ui

ui.hero("Вид", "Карточка вида: фото, распространение по областям и природным зонам")

q = st.text_input("Найти вид (латынь или русское название)", key="tx_q")
if q:
    found = db.search_taxa(q)
    if found.empty:
        st.info("Не найдено.")
    else:
        labels = {int(r["id"]): f'{r["name"]}' + (f' — {r["common_name_ru"]}' if r["common_name_ru"] else "")
                  for _, r in found.iterrows()}
        st.session_state["taxon_id"] = st.selectbox("Результаты", list(labels), format_func=labels.get)

tid = st.session_state.get("taxon_id") or st.query_params.get("id")
if not tid:
    st.info("Выберите вид поиском выше или кнопкой «Подробнее» на странице «Виды».")
    st.stop()

t = db.taxon(int(tid))
if not t:
    st.warning("Вид не найден в базе.")
    st.stop()

c1, c2 = st.columns([1, 2])
with c1:
    st.image(t.get("photo_url") or ui.PLACEHOLDER, use_container_width=True)
with c2:
    st.markdown(f"## {t.get('common_name_ru') or t['name']}")
    st.markdown(f"*{t['name']}*" + (f" · {t['common_name_en']}" if t.get("common_name_en") else ""))
    st.markdown(f"**Семейство:** {t.get('family') or '—'}  \n**Род:** {t.get('genus') or '—'}")
    links = [f"[iNaturalist]({t['inat_url']})"]
    if t.get("wikipedia_url"):
        links.append(f"[Википедия]({t['wikipedia_url']})")
    st.markdown(" · ".join(links))
    ar = db.taxon_areas(int(tid))
    if not ar.empty:
        r = ar[ar["kind"] == "region"]
        z = ar[ar["kind"] == "zone"]
        st.markdown(f"**Областей:** {len(r)} · **Природных зон:** {len(z)}")
        a, b = st.columns(2)
        a.dataframe(r[["name", "observations"]].rename(columns={"name": "Область", "observations": "Набл."}),
                    hide_index=True, use_container_width=True)
        b.dataframe(z[["name", "observations"]].rename(columns={"name": "Природная зона", "observations": "Набл."}),
                    hide_index=True, use_container_width=True)

obs = db.observations(taxon_id=int(tid), limit=5000)
st.subheader(f"Находки на карте ({len(obs)})")
layer_kind = st.radio("Подложка", ["Области", "Природные зоны"], horizontal=True, key="tx_layer")
ui.choropleth("region" if layer_kind == "Области" else "zone", points=obs, height=460)

if not obs.empty:
    st.subheader("Последние наблюдения")
    cols = st.columns(6)
    for i, (_, o) in enumerate(obs.head(12).iterrows()):
        with cols[i % 6]:
            if o.get("photo_url"):
                st.image(o["photo_url"], use_container_width=True)
            st.markdown(f"[{o.get('observed_on') or '—'}]({o['uri']})  \n"
                        f"<span class='muted'>{o.get('user_login') or ''} · {o.get('region') or ''}</span>",
                        unsafe_allow_html=True)

ui.footer()
