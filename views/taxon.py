import altair as alt
import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import lang, months, t, taxon_name

kind, name = ui.scope()

q = st.text_input(t("find_species"), key="tx_q")
if q:
    found = db.search_taxa(q)
    if found.empty:
        st.info(t("not_found"))
    else:
        opts = {int(r["id"]): f'{taxon_name(r, False) or ""} — {r["name"]} ({ui.fmt(r.get("n") or 0)})'
                for _, r in found.iterrows()}
        sel = st.selectbox(t("results"), list(opts), format_func=opts.get)
        st.query_params["id"] = str(sel)

tid = st.query_params.get("id")
if not tid:
    st.info(t("choose_species"))
    st.stop()
tid = int(tid)
d = db.taxon(tid)
tx = d.get("taxon") or {}
if not tx:
    st.warning(t("not_found"))
    st.stop()

kk = lang() == "kk"
st.markdown(f"## {ui.esc(taxon_name(tx))}")
sub = f"*{ui.esc(tx.get('name'))}*"
if kk and tx.get("common_name_ru"):
    sub += f" · {ui.esc(tx['common_name_ru'])}"
if not kk and tx.get("common_name_kk"):
    sub += f" · {ui.esc(tx['common_name_kk'])}"
if kk and not tx.get("common_name_kk"):
    sub += f" · <span class='muted'>({t('no_kk_name')})</span>"
st.markdown(sub, unsafe_allow_html=True)

c1, c2 = st.columns([1, 2])
with c1:
    st.image(tx.get("photo_url") or ui.PLACEHOLDER, use_container_width=True)
    st.markdown(f"**{t('family')}:** {tx.get('family') or '—'}  \n**{t('genus')}:** {tx.get('genus') or '—'}"
                + (f"  \n**{t('parent')}:** {tx['parent_name']}" if tx.get("parent_name") else ""))
    st.markdown(f"**{t('observations_n').capitalize()}:** {ui.fmt(d.get('observations'))}  \n"
                f"**{t('observers_n')}:** {ui.fmt(d.get('observers'))}")
    links = []
    wiki = tx.get("wiki_kk_url") if kk and tx.get("wiki_kk_url") else (tx.get("wiki_ru_url") or tx.get("wikipedia_url"))
    if wiki:
        links.append(f"[Wikipedia ↗]({wiki})")
    st.markdown(" · ".join(links))
with c2:
    ui.observations_map("all", "all", taxon=tid, mode="points", key="taxon_map", height=440)

# ---- описание ----
st.markdown(f"### {t('description')}")
desc = (tx.get("description_kk") or "") if kk else (tx.get("description_ru") or "")
if kk and not desc and tx.get("description_ru"):
    st.caption("Қазақша сипаттама әлі жоқ — орысша нұсқасы көрсетілген.")
    desc = tx.get("description_ru")
if desc:
    st.markdown(f'<div class="desc">{ui.esc(desc).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
else:
    st.info(t("no_description"))
b1, b2 = st.columns([1, 1])
if not ui.auth_token():
    b1.caption(t("need_account"))
    b1.page_link("views/account.py", label=t("btn_login"))
elif b1.button(t("wiki_btn"), use_container_width=True):
    with st.spinner("Wikipedia…"):
        try:
            w = db.fetch_wiki(tid, ui.auth_token())
            if w.get("message") and w["message"] != "ok":
                st.warning(w["message"])
            elif w.get("description_ru") or w.get("description_kk"):
                st.success(t("wiki_done"))
                st.rerun()
            else:
                st.info(t("wiki_none"))
        except Exception as e:
            st.error(str(e))
if ui.is_editor():
    with b2.popover(t("edit_taxon"), use_container_width=True):
        with st.form("edit_taxon"):
            cr = st.text_input(t("common_ru"), tx.get("common_name_ru") or "")
            ck = st.text_input(t("common_kk"), tx.get("common_name_kk") or "")
            dr = st.text_area(t("desc_ru"), tx.get("description_ru") or "", height=150)
            dk = st.text_area(t("desc_kk"), tx.get("description_kk") or "", height=150)
            if st.form_submit_button(t("save")):
                try:
                    db.write("api_edit_taxon", p_pwd=ui.auth_token(), p_id=tid, p_common_ru=cr,
                             p_common_kk=ck, p_desc_ru=dr, p_desc_kk=dk, p_editor=ui.auth()["name"])
                    st.success(t("saved"))
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
elif ui.auth_token():
    b2.caption(t("editors_only"))

# ---- сезонность и территории ----
MONTHS = months()
m = pd.DataFrame(d.get("months") or [])
a = pd.DataFrame(d.get("areas") or [])
c3, c4 = st.columns(2)
with c3:
    st.markdown(f"**{t('seasonality')}**")
    if not m.empty:
        m = pd.DataFrame({"month": range(1, 13)}).merge(m, how="left").fillna(0)
        m["m"] = m["month"].map(lambda i: MONTHS[int(i) - 1])
        st.altair_chart(alt.Chart(m).mark_bar(color=ui.GREEN).encode(
            x=alt.X("m:N", sort=MONTHS, title=None), y=alt.Y("n:Q", title=t("observations_n")),
            tooltip=[alt.Tooltip("m:N", title=t("month")), alt.Tooltip("n:Q", title=t("observations_n"))]),
            use_container_width=True)
with c4:
    st.markdown(f"**{t('where_found')}**")
    if not a.empty:
        names = {x["name"]: ui.area_name(x) for k2 in ("region", "zone") for x in db.areas(k2)}
        a["title"] = a["name"].map(lambda n: names.get(n, n))
        x1, x2 = st.columns(2)
        x1.dataframe(a[a["kind"] == "region"][["title", "n"]].rename(columns={"title": t("region"), "n": "N"}),
                     hide_index=True, use_container_width=True)
        x2.dataframe(a[a["kind"] == "zone"][["title", "n"]].rename(columns={"title": t("zone"), "n": "N"}),
                     hide_index=True, use_container_width=True)

# ---- добавленные наблюдения вида ----
u = db.user_observations(taxon=tid)
if not u.empty:
    st.markdown(f"**{t('user_obs')}**")
    cols = st.columns(4)
    for i, (_, r) in enumerate(u.head(8).iterrows()):
        with cols[i % 4]:
            if r.get("has_photo"):
                p = db.user_photo(int(r["id"]))
                if p.get("data"):
                    st.image(f"data:{p.get('mime') or 'image/jpeg'};base64,{p['data']}", use_container_width=True)
            st.caption(f"{r.get('subspecies') or ''} {r.get('author') or ''} · {r.get('observed_on') or ''}")

photos = pd.DataFrame(d.get("photos") or [])
if not photos.empty:
    st.markdown(f"**{t('photos_research')}**")
    cols = st.columns(6)
    for i, (_, p) in enumerate(photos.head(18).iterrows()):
        with cols[i % 6]:
            st.image(p["photo_url"], use_container_width=True)
            st.markdown(f"<span class='muted'>[{p.get('observed_on') or '—'}]({p['uri']}) · {ui.esc(p.get('user_login'))}</span>",
                        unsafe_allow_html=True)

if tid > 0:
    st.markdown(f"**{t('all_taxon_obs')}**")
    df, total = db.observations(kind, name, taxon=tid, limit=24)
    st.caption(f"{ui.fmt(total)} {t('observations_n')} · {ui.scope_label(kind, name)}")
    ui.observation_cards(df)
ui.footer()
