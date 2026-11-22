"""Распознавание вида по фото.

* Основной способ — собственный ИИ сайта (BioCLIP-2, см. lib/ai.py): без ключей и внешних служб.

* Растения — Pl@ntNet API (бесплатно до 500 запросов в день). Секрет: PLANTNET_API_KEY
  (ключ: https://my.plantnet.org → регистрация → «Settings / API key»).
* Животные и растения — iNaturalist Computer Vision. Секрет: INAT_API_TOKEN
  (выдаётся iNaturalist по запросу для приложений; без него этот способ скрыт).
Если ни одного ключа нет — блок распознавания не показывается.
"""
from __future__ import annotations

import io
import os

import requests
import streamlit as st


def _secret(name: str) -> str:
    try:
        v = st.secrets.get(name)
    except Exception:
        v = None
    return (v or os.getenv(name) or "").strip()


def available() -> dict:
    from lib import ai
    return {"own": ai.ready(), "plants": bool(_secret("PLANTNET_API_KEY")), "animals": bool(_secret("INAT_API_TOKEN"))}


def _jpeg(data: bytes, side: int = 1280) -> bytes:
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((side, side))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
        return buf.getvalue()
    except Exception:
        return data


def plantnet(data: bytes, organ: str = "auto", lang: str = "ru") -> list[dict]:
    key = _secret("PLANTNET_API_KEY")
    if not key:
        return []
    r = requests.post("https://my-api.plantnet.org/v2/identify/all",
                      params={"api-key": key, "lang": lang, "nb-results": 5, "include-related-images": "false"},
                      files=[("images", ("photo.jpg", _jpeg(data), "image/jpeg"))], data={"organs": [organ]},
                      timeout=60)
    if r.status_code == 404:          # «Species not found»
        return []
    r.raise_for_status()
    out = []
    for x in r.json().get("results", [])[:5]:
        sp = x.get("species") or {}
        out.append({"latin": sp.get("scientificNameWithoutAuthor"), "score": float(x.get("score") or 0),
                    "family": (sp.get("family") or {}).get("scientificNameWithoutAuthor"),
                    "common": ", ".join((sp.get("commonNames") or [])[:2]), "kingdom": "plantae", "source": "Pl@ntNet"})
    return out


def inat(data: bytes, lat: float | None = None, lng: float | None = None) -> list[dict]:
    tok = _secret("INAT_API_TOKEN")
    if not tok:
        return []
    form = {}
    if lat and lng:
        form.update({"lat": lat, "lng": lng})
    r = requests.post("https://api.inaturalist.org/v1/computervision/score_image",
                      headers={"Authorization": tok}, data=form,
                      files={"image": ("photo.jpg", _jpeg(data, 640), "image/jpeg")}, timeout=60)
    r.raise_for_status()
    out = []
    for x in r.json().get("results", [])[:5]:
        tx = x.get("taxon") or {}
        score = x.get("combined_score") or x.get("vision_score") or 0
        out.append({"latin": tx.get("name"), "score": float(score) / (100 if float(score) > 1 else 1),
                    "family": None, "common": tx.get("preferred_common_name") or "",
                    "kingdom": "animalia" if tx.get("iconic_taxon_name") not in ("Plantae", "Fungi") else "plantae",
                    "source": "CV"})
    return out


def identify(data: bytes, what: str, lat=None, lng=None, lang: str = "ru") -> list[dict]:
    """what: 'plant' | 'animal' | 'any'. Возвращает до 5 вариантов, лучшие первыми.
    Основной способ — собственный ИИ (lib/ai.py); ключи Pl@ntNet / iNaturalist не нужны (необязательная замена)."""
    av = available()
    if av["own"]:
        from lib import ai
        r = ai.identify(data, {"plant": "plantae", "animal": "animalia"}.get(what))
        st.session_state["rec_genus"] = (r.get("genus"), r.get("genus_score"))
        return r["results"]
    if what == "plant" and av["plants"]:
        return plantnet(data, lang=lang)
    if av["animals"]:
        return inat(data, lat, lng)
    if av["plants"]:
        return plantnet(data, lang=lang)
    return []
