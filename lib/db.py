"""Доступ к Supabase (PostgREST) только на чтение, с кешированием."""
from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

DEFAULT_URL = "https://ucrhksetkgmhoxdwwhnh.supabase.co"


def _cfg() -> tuple[str, str]:
    url = key = None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass
    url = url or os.getenv("SUPABASE_URL") or DEFAULT_URL
    key = key or os.getenv("SUPABASE_ANON_KEY")
    if not key:
        st.error(
            "Не задан ключ **SUPABASE_ANON_KEY**. Добавьте его в `.streamlit/secrets.toml` "
            "или в Settings → Secrets на Streamlit Cloud."
        )
        st.stop()
    return url.rstrip("/"), key


def _headers() -> dict:
    _, key = _cfg()
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _get(path: str, params: dict | None = None) -> list[dict]:
    url, _ = _cfg()
    r = requests.get(f"{url}/rest/v1/{path}", headers=_headers(), params=params, timeout=60)
    if r.status_code >= 300:
        st.error(f"Ошибка Supabase ({r.status_code}): {r.text[:300]}")
        st.stop()
    return r.json()


def _get_all(path: str, params: dict, page: int = 1000, cap: int = 50000) -> list[dict]:
    out, offset = [], 0
    while offset < cap:
        data = _get(path, {**params, "limit": page, "offset": offset})
        out += data
        if len(data) < page:
            break
        offset += page
    return out


def _rpc(fn: str, payload: dict) -> list[dict]:
    url, _ = _cfg()
    r = requests.post(f"{url}/rest/v1/rpc/{fn}", headers=_headers(), json=payload, timeout=60)
    if r.status_code >= 300:
        st.error(f"Ошибка Supabase ({r.status_code}): {r.text[:300]}")
        st.stop()
    return r.json()


TTL = 3600


@st.cache_data(ttl=TTL, show_spinner=False)
def project_stats() -> dict:
    d = _get("project_stats", {"select": "*"})
    return d[0] if d else {"observations": 0, "species": 0, "observers": 0, "last_observed": None}


@st.cache_data(ttl=TTL, show_spinner=False)
def area_stats(kind: str) -> pd.DataFrame:
    df = pd.DataFrame(_get("area_stats", {"select": "*", "kind": f"eq.{kind}", "order": "species.desc"}))
    return df if not df.empty else pd.DataFrame(columns=["kind", "name", "species", "observations", "observers"])


@st.cache_data(ttl=TTL, show_spinner=False)
def areas(kind: str) -> list[dict]:
    return _get("areas", {"select": "name,name_en,geojson", "kind": f"eq.{kind}", "order": "name"})


@st.cache_data(ttl=TTL, show_spinner=False)
def family_stats(limit: int = 15) -> pd.DataFrame:
    return pd.DataFrame(_get("family_stats", {"select": "*", "order": "species.desc", "limit": limit}))


@st.cache_data(ttl=TTL, show_spinner=False)
def observer_stats(limit: int = 15) -> pd.DataFrame:
    return pd.DataFrame(_get("observer_stats", {"select": "*", "order": "observations.desc", "limit": limit}))


@st.cache_data(ttl=TTL, show_spinner=False)
def species_list(kind: str = "all", name: str | None = None, q: str = "", limit: int = 48, offset: int = 0):
    data = _rpc("species_list", {"p_kind": kind, "p_name": name, "p_q": q or None,
                                 "p_limit": limit, "p_offset": offset})
    df = pd.DataFrame(data)
    total = int(df["total_count"].iloc[0]) if not df.empty else 0
    return df, total


@st.cache_data(ttl=TTL, show_spinner=False)
def taxon(taxon_id: int) -> dict | None:
    d = _get("taxa", {"select": "*", "id": f"eq.{taxon_id}"})
    return d[0] if d else None


@st.cache_data(ttl=TTL, show_spinner=False)
def search_taxa(q: str, limit: int = 30) -> pd.DataFrame:
    q = q.replace(",", " ").replace("(", " ").replace(")", " ").strip()
    return pd.DataFrame(_get("taxa", {
        "select": "id,name,common_name_ru",
        "or": f"(name.ilike.*{q}*,common_name_ru.ilike.*{q}*)",
        "order": "name", "limit": limit,
    }))


@st.cache_data(ttl=TTL, show_spinner=False)
def taxon_areas(taxon_id: int) -> pd.DataFrame:
    return pd.DataFrame(_get("taxon_areas", {"select": "kind,name,observations",
                                             "taxon_id": f"eq.{taxon_id}", "order": "observations.desc"}))


@st.cache_data(ttl=TTL, show_spinner=False)
def observations(taxon_id: int | None = None, kind: str = "all", name: str | None = None,
                 limit: int = 5000) -> pd.DataFrame:
    params = {"select": "id,taxon_id,observed_on,lat,lng,quality_grade,user_login,photo_url,uri,region,zone",
              "order": "id.desc"}
    if taxon_id:
        params["taxon_id"] = f"eq.{taxon_id}"
    if kind in ("region", "zone") and name:
        params[kind] = f"eq.{name}"
    return pd.DataFrame(_get_all("observations", params, cap=limit))
