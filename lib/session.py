"""Вход сохраняется в cookie браузера: после перехода по ссылке (перезагрузки страницы)
пользователь остаётся залогиненным, и редактор видит свои инструменты."""
import streamlit as st
import streamlit.components.v1 as components

from lib import db

COOKIE = "flora_auth"


def restore():
    """Если в этой сессии ещё не вошли — пробуем войти по токену из cookie (один раз за сессию)."""
    if st.session_state.get("auth") or st.session_state.get("_cookie_checked"):
        return
    st.session_state["_cookie_checked"] = True
    try:
        tok = st.context.cookies.get(COOKIE)
    except Exception:
        tok = None
    if not tok:
        return
    try:
        me = db.write("api_me", p_token=tok)
        if isinstance(me, dict) and me.get("token"):
            st.session_state.auth = me
            st.session_state["_cookie_val"] = me["token"]
    except Exception:
        pass


def sync_cookie():
    """Записывает/стирает cookie, когда пользователь вошёл или вышел (вход по паролю редактора не сохраняем)."""
    a = st.session_state.get("auth") or {}
    want = a.get("token", "") if a.get("login") != "editor" else ""
    if st.session_state.get("_cookie_val") == want:
        return
    st.session_state["_cookie_val"] = want
    age = 2592000 if want else 0
    js = (f'document.cookie = "{COOKIE}={want}; path=/; max-age={age}; SameSite=Lax; Secure";'
          f'try {{ parent.document.cookie = "{COOKIE}={want}; path=/; max-age={age}; SameSite=Lax; Secure"; }} catch (e) {{}}')
    with st.sidebar:
        components.html(f"<script>{js}</script>", height=0)
