"""Собственный ИИ-распознаватель видов (BioCLIP-2, int8 ONNX) — работает на сервере сайта, без ключей и внешних служб.

Модель и справочник видов готовит GitHub Actions (tools/ai_build.py):
  data/ai/species.json, data/ai/text_emb.npy, data/ai/config.json — в репозитории;
  bioclip2_visual_int8.onnx (~300 МБ) — в GitHub Release «ai-model», скачивается один раз при первом распознавании.
"""
from __future__ import annotations

import io
import json
import os
import pathlib

import numpy as np
import requests
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent.parent / "data" / "ai"
MODEL_URL = "https://github.com/aidarpavl/flora-kz/releases/download/ai-model/bioclip2_visual_int8.onnx"
CACHE = pathlib.Path(os.getenv("FLORA_AI_CACHE", pathlib.Path.home() / ".cache" / "flora_ai"))


def ready() -> bool:
    """Справочник видов собран и библиотека onnxruntime установлена."""
    if not all((ROOT / f).exists() for f in ("species.json", "text_emb.npy", "config.json")):
        return False
    try:
        import onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _data():
    cfg = json.loads((ROOT / "config.json").read_text())
    species = json.loads((ROOT / "species.json").read_text(encoding="utf-8"))
    emb = np.load(ROOT / "text_emb.npy").astype(np.float32)
    return cfg, species, emb


def _model_path() -> pathlib.Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / "bioclip2_visual_int8.onnx"
    if p.exists() and p.stat().st_size > 50_000_000:
        return p
    tmp = p.with_suffix(".part")
    with requests.get(MODEL_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(p)
    return p


@st.cache_resource(show_spinner=False)
def _session():
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = 2
    so.inter_op_num_threads = 1
    so.enable_mem_pattern = False
    return ort.InferenceSession(str(_model_path()), so, providers=["CPUExecutionProvider"])


def _prep(data: bytes, size: int, mean, std) -> np.ndarray:
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    w, h = img.size
    s = size / min(w, h)
    img = img.resize((max(size, round(w * s)), max(size, round(h * s))), Image.BICUBIC)
    w, h = img.size
    l, t = (w - size) // 2, (h - size) // 2
    a = np.asarray(img.crop((l, t, l + size, t + size)), dtype=np.float32) / 255.0
    a = (a - np.array(mean, np.float32)) / np.array(std, np.float32)
    return a.transpose(2, 0, 1)[None]


def _embed(data: bytes) -> np.ndarray:
    cfg, _, _ = _data()
    sess = _session()
    x = _prep(data, cfg["size"], cfg["mean"], cfg["std"])
    # усреднение с зеркальным отражением — немного устойчивее
    e = sess.run(None, {"image": np.concatenate([x, x[:, :, :, ::-1].copy()])})[0]
    e = e.mean(0)
    return e / np.linalg.norm(e)


def identify(data: bytes, kingdom: str | None = None, top: int = 5) -> dict:
    """kingdom: 'plantae' | 'animalia' | None. Возвращает варианты видов и подсказку по роду."""
    cfg, species, emb = _data()
    e = _embed(data)
    logits = cfg.get("logit_scale", 100.0) * (emb @ e)
    if kingdom:
        kname = "Plantae" if kingdom == "plantae" else "Animalia"
        mask = np.array([s.get("kingdom") == kname for s in species])
        logits = np.where(mask, logits, -1e9)
    p = np.exp(logits - logits.max())
    p /= p.sum()
    order = np.argsort(-p)[:top]
    out = []
    for i in order:
        s = species[int(i)]
        out.append({"latin": s["species"], "score": float(p[i]), "family": s.get("family"), "genus": s.get("genus"),
                    "common": s.get("vernacular") or "", "redbook": bool(s.get("redbook")),
                    "kingdom": "plantae" if s.get("kingdom") == "Plantae" else "animalia", "source": "BioCLIP-2"})
    # суммарная вероятность по родам — если вид неуверен, род обычно определяется надёжнее
    g = {}
    for i in np.argsort(-p)[:200]:
        s = species[int(i)]
        g[s.get("genus")] = g.get(s.get("genus"), 0.0) + float(p[i])
    genus, gp = max(g.items(), key=lambda kv: kv[1]) if g else (None, 0.0)
    return {"results": out, "genus": genus, "genus_score": gp}


def report() -> dict:
    try:
        return json.loads((ROOT / "report.json").read_text())
    except Exception:
        return {}
