"""Доступ к Supabase: RPC-функции api_* (только чтение) с кешированием."""
from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

DEFAULT_URL = "https://ucrhksetkgmhoxdwwhnh.supabase.co"
TTL = 600


def _cfg() -> tuple[str, str]:
    url = key = None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass
    url = (url or os.getenv("SUPABASE_URL") or DEFAULT_URL).strip().rstrip("/")
    key = (key or os.getenv("SUPABASE_ANON_KEY") or "").strip()
    if not key:
        st.error("Не задан ключ **SUPABASE_ANON_KEY**. Добавьте его в `.streamlit/secrets.toml` "
                 "или в Settings → Secrets на Streamlit Cloud.")
        st.stop()
    return url, key


@st.cache_data(ttl=TTL, show_spinner=False)
def rpc(fn: str, **params):
    """Вызов функции public.<fn> через PostgREST. Возвращает разобранный JSON."""
    url, key = _cfg()
    headers = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    payload = {k: v for k, v in params.items() if v is not None}
    r = requests.post(f"{url}/rest/v1/rpc/{fn}", headers=headers, json=payload, timeout=90)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase {fn}: {r.status_code} {r.text[:300]}")
    return r.json()


def safe(fn: str, default=None, **params):
    try:
        return rpc(fn, **params)
    except Exception as e:  # показываем ошибку, но не роняем страницу
        st.warning(f"Не удалось получить данные ({fn}): {e}")
        return default


# ---------- удобные обёртки ----------

def stats(kind, name) -> dict:
    return safe("api_stats", {}, p_kind=kind, p_name=name) or {}


def species(kind, name, q="", limit=48, offset=0) -> tuple[pd.DataFrame, int]:
    d = safe("api_species", {"total": 0, "rows": []}, p_kind=kind, p_name=name, p_q=q or None,
             p_limit=limit, p_offset=offset)
    return pd.DataFrame(d.get("rows") or []), int(d.get("total") or 0)


def observers(kind, name, sort="observations", limit=50, offset=0) -> tuple[pd.DataFrame, int]:
    d = safe("api_observers", {"total": 0, "rows": []}, p_kind=kind, p_name=name, p_sort=sort,
             p_limit=limit, p_offset=offset)
    return pd.DataFrame(d.get("rows") or []), int(d.get("total") or 0)


def identifiers(kind, name, limit=50, offset=0) -> tuple[pd.DataFrame, int]:
    d = safe("api_identifiers", {"total": 0, "rows": []}, p_kind=kind, p_name=name,
             p_limit=limit, p_offset=offset)
    return pd.DataFrame(d.get("rows") or []), int(d.get("total") or 0)


def observations(kind, name, taxon=None, user=None, quality=None, q=None,
                 date_from=None, date_to=None, limit=48, offset=0) -> tuple[pd.DataFrame, int]:
    d = safe("api_observations", {"total": 0, "rows": []}, p_kind=kind, p_name=name, p_taxon=taxon,
             p_user=user or None, p_quality=quality, p_q=q or None,
             p_date_from=str(date_from) if date_from else None,
             p_date_to=str(date_to) if date_to else None, p_limit=limit, p_offset=offset)
    return pd.DataFrame(d.get("rows") or []), int(d.get("total") or 0)


def map_cells(kind, name) -> pd.DataFrame:
    d = safe("api_map_cells", [], p_kind=kind, p_name=name) or []
    return pd.DataFrame(d, columns=["lng", "lat", "n"])


def map_points(kind, name, taxon=None, user=None, quality=None, limit=20000) -> pd.DataFrame:
    d = safe("api_map_points", [], p_kind=kind, p_name=name, p_taxon=taxon, p_user=user or None,
             p_quality=quality, p_limit=limit) or []
    return pd.DataFrame(d, columns=["id", "lng", "lat", "title", "sci", "quality", "user", "date"])


def months(kind, name) -> pd.DataFrame:
    return pd.DataFrame(safe("api_months", [], p_kind=kind, p_name=name) or [])


def families(kind, name, limit=30) -> pd.DataFrame:
    return pd.DataFrame(safe("api_families", [], p_kind=kind, p_name=name, p_limit=limit) or [])


def areas(kind) -> list[dict]:
    return safe("api_areas", [], p_kind=kind) or []


def taxon(taxon_id: int) -> dict:
    return safe("api_taxon", {}, p_id=int(taxon_id)) or {}


def search_taxa(q: str) -> pd.DataFrame:
    return pd.DataFrame(safe("api_search_taxa", [], p_q=q, p_limit=30) or [])


def progress() -> dict:
    return safe("api_progress", {}) or {}


# ---------- добавленные наблюдения, Википедия, редактирование ----------

def user_observations(taxon=None, kind="all", name="all", limit=500) -> pd.DataFrame:
    return pd.DataFrame(safe("api_user_observations", [], p_taxon=taxon, p_kind=kind, p_name=name,
                             p_limit=limit) or [])


def user_photo(obs_id: int) -> dict:
    return safe("api_user_photo", {}, p_id=int(obs_id)) or {}


def write(fn: str, **params):
    """Вызов без кеша (запись). После успеха кеш чтения сбрасывается."""
    url, key = _cfg()
    headers = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    r = requests.post(f"{url}/rest/v1/rpc/{fn}", headers=headers, json=params, timeout=90)
    if r.status_code >= 300:
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            msg = r.text
        raise RuntimeError(msg)
    rpc.clear()
    return r.json()


def editor_login(pwd: str) -> bool:
    try:
        return bool(write("api_editor_login", p_pwd=pwd))
    except Exception:
        return False


def fetch_wiki(taxon_id: int) -> dict:
    return write("api_fetch_wiki", p_id=int(taxon_id)) or {}
