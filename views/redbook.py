"""Красная книга Казахстана: каталог, карточка вида, добавление/правка (RU/KZ), точки и ареалы на карте."""
import base64
import io
import json
from datetime import date

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw

from lib import db, ui
from lib.i18n import area_name, lang, t

KK = lang() == "kk"
from lib.rb import CATS, cat_label, cat_color, nm, txt, card_img, fam, photo_uri, to_b64, page_link  # noqa: E402
from lib.rb import add_layers as add_rb_layers  # noqa: E402
from lib import rb  # noqa: E402

KING = rb.kingdom()
ANIMAL = rb.animal()


@st.cache_data(ttl=600, show_spinner=False)
def thumb_uri(sid: int, stamp: str):
    """Уменьшенная копия загруженного фото для карточки (полное фото — на странице вида)."""
    full = photo_uri(sid)
    if not full:
        return None
    try:
        from PIL import Image
        raw = base64.b64decode(full.split(",", 1)[1])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.thumbnail((400, 400))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=80)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return full


def catalog_img(r):
    if r.get("has_photo"):
        return thumb_uri(int(r["id"]), str(r.get("updated_at") or "")) or ui.PLACEHOLDER
    u = r.get("photo_url")
    return u if isinstance(u, str) and u else ui.PLACEHOLDER


def sub(r):
    """Подпись под названием: для животных — класс · отряд, для растений — семейство."""
    if ANIMAL:
        c = (r.get("class_kk") or r.get("class_ru")) if KK else r.get("class_ru")
        o = (r.get("order_kk") or r.get("order_ru")) if KK else r.get("order_ru")
        return " · ".join(x for x in (c, o, r.get("family")) if isinstance(x, str) and x) or "—"
    return fam(r)


kind, name = ui.scope()
ui.header()
st.subheader(f"{rb.icon()} {rb.title()}")
st.caption(rb.L("Виды и подвиды животных из Красной книги РК: систематика (тип, класс, отряд, семейство), фото, "
                "описания на двух языках и места обитания на карте. Редакторы могут всё изменять."
                , "ҚР Қызыл кітабына енген жануарлар түрлері мен түр тармақтары: жүйелеу, сурет, екі тілдегі сипаттама "
                "және картадағы мекендеу орындары. Редакторлар бәрін өзгерте алады.") if ANIMAL else t("rb_intro"))
st.markdown(" ".join(f'<span style="display:inline-block;margin:0 10px 6px 0;padding:2px 10px;border-radius:10px;'
                     f'background:{v[2]};color:#fff;font-size:.82rem">{v[1] if KK else v[0]}</span>'
                     for v in CATS.values()), unsafe_allow_html=True)

tab_cat, tab_card, tab_edit = st.tabs([t("rb_tab_catalog"), t("rb_tab_card"), t("rb_tab_edit")])

# ======================= КАТАЛОГ =======================
with tab_cat:
    f1, f2 = st.columns([3, 2])
    q = f1.text_input(t("species_search"), key="rb_q")
    cat = f2.selectbox(t("rb_category"), [""] + list(CATS), format_func=lambda c: cat_label(c) if c else t("rb_cat_any"),
                       key="rb_cat")
    rows = pd.DataFrame(db.safe("api_rb_list", [], p_kind=kind, p_name=name, p_q=q or None, p_category=cat or None, p_kingdom=KING) or [])
    st.markdown(f"**{ui.fmt(len(rows))}** {t('rb_species_n')} · {ui.scope_label(kind, name)}")
    if rows.empty:
        st.info(t("rb_empty"))
    else:
        parts = []
        for _, r in rows.iterrows():
            img = ui.esc(catalog_img(r))
            parts.append(
                f'<div class="card"><a href="{page_link(r["id"])}" target="_self">'
                f'<div class="ph"><img src="{img}" alt="" loading="lazy" '
                f'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">'
                f'<div class="badge" style="background:{cat_color(r.get("category"))}">{ui.esc(cat_label(r.get("category")))}'
                f' · 📍{int(r["n_points"])} · ⬟{int(r["n_ranges"])}</div></div>'
                f'<div class="b"><div class="cn">{ui.esc(nm(r))}</div><div class="sn">{ui.esc(r["latin"])}'
                f'{" (" + ui.esc(r["parent_latin"]) + ")" if isinstance(r.get("parent_latin"), str) and r.get("parent_latin") else ""}</div>'
                f'<div class="sn" style="font-style:normal;color:#888">{ui.esc(sub(r))}</div></div></a></div>')
        st.markdown(f'<div class="grid">{"".join(parts)}</div>', unsafe_allow_html=True)

    st.markdown(f"#### {t('obs_map')}")
    mp = db.safe("api_rb_map", {}, p_kind=kind, p_name=name, p_auth=ui.auth_token(), p_kingdom=KING) or {}
    pts = [{"lat": p[0], "lng": p[1], "category": p[6],
            "title": f"{(p[5] or p[4] or p[3]) if KK else (p[4] or p[3])} · {p[3]}"} for p in mp.get("points", [])]
    m = ui.base_map()
    ui.add_borders(m, "zone" if kind == "zone" else "region", name if kind != "all" else None)
    add_rb_layers(m, pts, mp.get("ranges", []))
    ui.show_map(m, key="rb_overview", height=520)

# ======================= КАРТОЧКА =======================
with tab_card:
    allrows = pd.DataFrame(db.safe("api_rb_list", [], p_kingdom=KING) or [])
    if allrows.empty:
        st.info(t("rb_empty"))
    else:
        opts = {int(r["id"]): f'{nm(r)} — {r["latin"]} ({cat_label(r.get("category"))})' for _, r in allrows.iterrows()}
        sid = st.selectbox(t("rb_choose"), list(opts), format_func=opts.get, key="rb_card_sel")
        d = db.safe("api_rb_get", {}, p_id=sid, p_auth=ui.auth_token()) or {}
        s = d.get("species") or {}
        st.markdown(f'<a href="{page_link(sid)}" target="_self">📄 {"Түр бетін ашу" if KK else "Открыть страницу вида"} →</a>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(card_img(s), use_container_width=True)
            if s.get("photo_attr") and not s.get("has_photo"):
                st.caption("📷 " + s["photo_attr"])
            st.markdown(f'<span style="padding:3px 10px;border-radius:10px;background:{cat_color(s.get("category"))};'
                        f'color:#fff">{ui.esc(cat_label(s.get("category")))}</span>', unsafe_allow_html=True)
            st.markdown(f"## {ui.esc(nm(s))}")
            st.markdown(f"*{ui.esc(s.get('latin'))}*" + (f" · {ui.esc(s['name_ru'])}" if KK and s.get("name_ru") else "")
                        + (f" · {ui.esc(s['name_kk'])}" if not KK and s.get("name_kk") else ""))
            rank = {"species": t("r_species"), "subspecies": t("r_subspecies"), "variety": t("r_variety"),
                    "form": t("r_form")}.get(s.get("rank"), s.get("rank"))
            st.markdown(f"**{t('taxon_rank')}:** {rank}" + (f"  \n**{t('parent')}:** *{s['parent_latin']}*" if s.get("parent_latin") else "")
                        + (f"  \n{rb.tax_lines(s)}" if ANIMAL and rb.tax_lines(s) else "")
                        + f"  \n**{t('family')}:** {fam(s)}"
                        + f"  \n**{'Туыс' if KK else 'Род'}:** *{s.get('genus') or '—'}*"
                        + f"  \n**{'Түр' if KK else 'Вид'}:** *{s.get('latin')}*"
                        + f"  \n**{t('author')}:** {s.get('author') or '—'}")
            links = []
            wiki = (s.get("wiki_kk_url") or s.get("wiki_ru_url")) if KK else s.get("wiki_ru_url")
            if wiki:
                links.append(f"[Wikipedia ↗]({wiki})")
            if s.get("gbif_key"):
                links.append(f"[GBIF ↗](https://www.gbif.org/species/{s['gbif_key']})")
            if s.get("taxon_id"):
                links.append(f"[{t('rb_in_inat')} →]({ui.taxon_link(s['taxon_id'])})")
            st.markdown(" · ".join(links))
        with c2:
            m = ui.base_map()
            ui.add_borders(m, "region")
            pts = [{"lat": p["lat"], "lng": p["lng"], "category": s.get("category"),
                    "title": f"{nm(s)} · {p.get('observed_on') or ''} {txt(p, 'note')}"} for p in d.get("points", [])]
            rngs = [{**g, "category": s.get("category"), "latin": s.get("latin"), "name_ru": s.get("name_ru"),
                     "name_kk": s.get("name_kk")} for g in d.get("ranges", [])]
            add_rb_layers(m, pts, rngs)
            ui.show_map(m, key=f"rb_card_map_{sid}", height=430)
            st.caption((t("rb_precise") if d.get("precise") else t("rb_rounded"))
                       + f" · 📍 {len(pts)} {t('rb_points')} · ⬟ {len(rngs)} {t('rb_ranges')}")
        for title, base in ((t("description"), "description"), (t("rb_habitat"), "habitat"), (t("rb_protection"), "protection")):
            text = txt(s, base)
            if text:
                st.markdown(f"#### {title}")
                st.markdown(f'<div class="desc">{ui.esc(text).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        if not txt(s, "description"):
            st.info(t("no_description"))

# ======================= ДОБАВИТЬ / ИЗМЕНИТЬ =======================
with tab_edit:
    A = ui.auth_token()
    if not A:
        st.info(t("need_account"))
        st.page_link("views/account.py", label=t("btn_login"))
    else:
        allrows = pd.DataFrame(db.safe("api_rb_list", [], p_kingdom=KING) or [])
        opts = {0: t("rb_new")}
        if not allrows.empty:
            opts.update({int(r["id"]): f'{nm(r)} — {r["latin"]}' for _, r in allrows.iterrows()})
        if "rb_pending" in st.session_state:          # выбрать только что сохранённый / сбросить после удаления
            pend = st.session_state.pop("rb_pending")
            st.session_state["rb_edit_sel"] = pend if pend in opts else 0
        sid = st.selectbox(t("rb_edit_which"), list(opts), format_func=opts.get, key="rb_edit_sel") or None
        s = ((db.safe("api_rb_get", {}, p_id=sid, p_auth=A) or {}).get("species") or {}) if sid else {}

        # ---- 1. вид: названия, категория, тексты на двух языках, фото ----
        ranks = {"species": t("r_species"), "subspecies": t("r_subspecies"), "variety": t("r_variety"), "form": t("r_form")}
        with st.form(f"rb_form_{sid or 0}"):
            a, b = st.columns(2)
            latin = a.text_input(t("latin") + " *", s.get("latin") or "")
            rank = b.selectbox(t("taxon_rank"), list(ranks), index=list(ranks).index(s.get("rank") or "species"),
                               format_func=ranks.get)
            name_ru = a.text_input(t("common_ru"), s.get("name_ru") or "")
            name_kk = b.text_input(t("common_kk"), s.get("name_kk") or "")
            parent = a.text_input(t("parent"), s.get("parent_latin") or "")
            family = b.text_input(t("family"), s.get("family") or "")
            cat = st.selectbox(t("rb_category"), list(CATS), index=list(CATS).index(s["category"]) if s.get("category") in CATS else 1,
                               format_func=cat_label)
            d_ru = a.text_area(t("desc_ru"), s.get("description_ru") or "", height=160)
            d_kk = b.text_area(t("desc_kk"), s.get("description_kk") or "", height=160)
            h_ru = a.text_area(t("rb_habitat_ru"), s.get("habitat_ru") or "", height=100)
            h_kk = b.text_area(t("rb_habitat_kk"), s.get("habitat_kk") or "", height=100)
            p_ru = a.text_area(t("rb_protect_ru"), s.get("protection_ru") or "", height=100)
            p_kk = b.text_area(t("rb_protect_kk"), s.get("protection_kk") or "", height=100)
            photo = st.file_uploader(t("upload_photo"), type=["jpg", "jpeg", "png", "webp"])
            saved = st.form_submit_button(t("rb_save_species"), type="primary")
        if saved:
            b64, mime = to_b64(photo)
            try:
                r = db.write("api_rb_save", p_auth=A, p_id=sid, p_latin=latin, p_name_ru=name_ru, p_name_kk=name_kk,
                             p_rank=rank, p_parent_latin=parent, p_family=family, p_category=cat,
                             p_desc_ru=d_ru, p_desc_kk=d_kk, p_habitat_ru=h_ru, p_habitat_kk=h_kk,
                             p_protect_ru=p_ru, p_protect_kk=p_kk, p_photo_b64=b64, p_photo_mime=mime)
                if ANIMAL and not sid:   # новый вид в разделе животных
                    db.write("api_rb_save_ext", p_auth=A, p_id=int(r["id"]), p_fields={"kingdom": "animalia"},
                             p_photo_b64=None, p_photo_mime=None)
                st.success(f"{t('saved')} (id {r.get('id')})")
                st.session_state["rb_pending"] = int(r["id"])
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if sid:
            # ---- 2. описание из Википедии ----
            w1, w2 = st.columns([1, 2])
            ow = w2.checkbox(t("rb_wiki_overwrite"), key=f"rb_ow_{sid}")
            if w1.button(t("wiki_btn"), key=f"rb_wiki_{sid}", use_container_width=True):
                try:
                    r = db.write("api_rb_wiki", p_auth=A, p_id=sid, p_overwrite=ow)
                    if r.get("message"):
                        st.warning(r["message"])
                    elif r.get("ru") or r.get("kk"):
                        st.success(t("wiki_done"))
                        st.rerun()
                    else:
                        st.info(t("wiki_none"))
                except Exception as e:
                    st.error(str(e))

            # ---- 3. точки и ареал на карте ----
            st.markdown(f"#### {t('rb_objects')}")
            st.caption(t("rb_draw_hint"))
            d = db.safe("api_rb_get", {}, p_id=sid, p_auth=A) or {}
            m = ui.base_map()
            ui.add_borders(m, "region")
            add_rb_layers(m, [{"lat": p["lat"], "lng": p["lng"], "category": s.get("category"), "title": f"#{p['id']}"}
                              for p in d.get("points", [])],
                          [{**g, "category": s.get("category"), "latin": s.get("latin")} for g in d.get("ranges", [])])
            Draw(export=False, position="topleft",
                 draw_options={"polyline": False, "circle": False, "circlemarker": False,
                               "marker": True, "polygon": True, "rectangle": True},
                 edit_options={"edit": False}).add_to(m)
            out = ui.show_map(m, key=f"rb_draw_{sid}", height=520, returned=["all_drawings"])
            drawings = (out or {}).get("all_drawings") or []
            new_pts = [g for g in drawings if (g.get("geometry") or {}).get("type") == "Point"]
            new_rng = [g for g in drawings if (g.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]
            st.caption(t("rb_drawn", p=len(new_pts), r=len(new_rng)))
            n1, n2, n3 = st.columns([2, 2, 1])
            note_ru = n1.text_input(t("rb_note_ru"), key=f"rb_nru_{sid}")
            note_kk = n2.text_input(t("rb_note_kk"), key=f"rb_nkk_{sid}")
            pdate = n3.date_input(t("obs_date"), value=date.today(), key=f"rb_pd_{sid}", format="DD.MM.YYYY")
            if st.button(t("rb_save_drawings"), type="primary", disabled=not drawings, key=f"rb_sd_{sid}"):
                ok, errs = 0, []
                for g in new_pts:
                    lng, lat = g["geometry"]["coordinates"][:2]
                    try:
                        db.write("api_rb_add_point", p_auth=A, p_species=sid, p_lat=lat, p_lng=lng,
                                 p_note_ru=note_ru, p_note_kk=note_kk, p_date=str(pdate))
                        ok += 1
                    except Exception as e:
                        errs.append(str(e))
                for g in new_rng:
                    try:
                        db.write("api_rb_add_range", p_auth=A, p_species=sid, p_geojson=json.dumps(g["geometry"]),
                                 p_note_ru=note_ru, p_note_kk=note_kk)
                        ok += 1
                    except Exception as e:
                        errs.append(str(e))
                if ok:
                    st.success(f"{t('saved')}: {ok}")
                for e in errs:
                    st.error(e)
                if ok and not errs:
                    st.rerun()

            # ---- 4. удаление точек/ареалов/вида ----
            with st.expander(t("delete")):
                objs = {f"point:{p['id']}": f"📍 #{p['id']} · {p['lat']}, {p['lng']} · {p.get('region') or ''}"
                        for p in d.get("points", [])}
                objs.update({f"range:{g['id']}": f"⬟ #{g['id']} · {ui.fmt(g.get('area_km2'))} км²" for g in d.get("ranges", [])})
                if objs:
                    pick = st.selectbox(t("rb_objects"), list(objs), format_func=objs.get, key=f"rb_del_{sid}")
                    if st.button(t("delete"), key=f"rb_delbtn_{sid}"):
                        what, oid = pick.split(":")
                        try:
                            db.write("api_rb_delete", p_auth=A, p_what=what, p_id=int(oid))
                            st.success(t("deleted"))
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                if st.button(t("rb_delete_species"), key=f"rb_delsp_{sid}"):
                    try:
                        db.write("api_rb_delete", p_auth=A, p_what="species", p_id=int(sid))
                        st.session_state["rb_pending"] = 0
                        st.success(t("deleted"))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
ui.footer()
