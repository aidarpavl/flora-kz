"""Сборка собственного распознавателя видов (запускается в GitHub Actions, см. .github/workflows/ai-build.yml).

1. Список кандидатов: все виды растений и животных с находками в Казахстане (GBIF) + все виды Красной книги РК.
2. BioCLIP-2 (открытая модель, обучена на 214 млн фото живых организмов): текстовые эмбеддинги
   для каждого вида по полной систематике (царство … вид).
3. Визуальная часть модели -> ONNX -> int8 (≈300 МБ), чтобы работала на сервере сайта без видеокарты.
4. Проверка точности на реальных фото из GBIF (виды выбираются случайно) — числа пишутся в data/ai/report.json.

Результат: data/ai/species.json, data/ai/text_emb.npy (float16), data/ai/config.json, data/ai/report.json
и файл модели bioclip2_visual_int8.onnx (выкладывается в GitHub Release).
"""
from __future__ import annotations

import io
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
import torch
from PIL import Image

OUT = "data/ai"
GBIF = "https://api.gbif.org/v1"
KINGDOMS = {"Plantae": 6, "Animalia": 1}
S = requests.Session()
S.headers["User-Agent"] = "flora-kz-ai-build (github.com/aidarpavl/flora-kz)"
RANKS = ["kingdom", "phylum", "class", "order", "family", "genus"]


def get(url, **params):
    for i in range(5):
        try:
            r = S.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 + 3 * i)
    return None


def kz_species_keys():
    keys = {}
    for kname, kkey in KINGDOMS.items():
        off = 0
        while True:
            j = get(f"{GBIF}/occurrence/search", country="KZ", kingdomKey=kkey, limit=0, facet="speciesKey",
                    facetLimit=5000, facetOffset=off, facetMincount=1)
            counts = ((j or {}).get("facets") or [{}])[0].get("counts", []) if j else []
            for c in counts:
                keys[int(c["name"])] = int(c["count"])
            print(kname, "offset", off, "->", len(counts), flush=True)
            if len(counts) < 5000:
                break
            off += 5000
    return keys


def taxon(key):
    j = get(f"{GBIF}/species/{key}")
    if not j or j.get("rank") not in ("SPECIES",) or not j.get("species"):
        return None
    return {"key": key, "species": j["species"], **{r: j.get(r) for r in RANKS},
            "vernacular": j.get("vernacularName")}


def match(kingdom, name):
    j = get(f"{GBIF}/species/match", name=name, kingdom=kingdom, verbose="false")
    if not j or not j.get("speciesKey"):
        return None
    return int(j["speciesKey"])


def taxon_string(t):
    parts = [t.get(r) for r in RANKS] + [t["species"].split(" ", 1)[1] if " " in t["species"] else t["species"]]
    return " ".join(p for p in parts if p)


def main():
    os.makedirs(OUT, exist_ok=True)
    keys = kz_species_keys()
    print("GBIF KZ species:", len(keys), flush=True)
    rb = [l.rstrip("\n").split("\t") for l in open(f"{OUT}/redbook.tsv", encoding="utf-8") if l.strip()]
    with ThreadPoolExecutor(16) as ex:
        rb_keys = list(ex.map(lambda x: (x[1], match(x[0], " ".join(x[1].split()[:2]))), rb))
    rb_set = set()
    for name, k in rb_keys:
        if k:
            keys.setdefault(k, 0)
            rb_set.add(k)
        else:
            print("Red Book not matched:", name, flush=True)
    with ThreadPoolExecutor(24) as ex:
        taxa = [t for t in ex.map(taxon, list(keys)) if t]
    # один вид — одна строка (синонимы GBIF сводятся к принятому имени)
    uniq = {}
    for t in taxa:
        t["n_kz"] = keys.get(t["key"], 0)
        t["redbook"] = t["key"] in rb_set
        u = uniq.get(t["species"])
        if not u or t["n_kz"] > u["n_kz"]:
            uniq[t["species"]] = {**t, "redbook": t["redbook"] or bool(u and u["redbook"])}
    taxa = sorted(uniq.values(), key=lambda t: (t["kingdom"] or "", t["species"]))
    print("candidate species:", len(taxa), flush=True)

    import open_clip
    model, _, preprocess = open_clip.create_model_and_transforms("hf-hub:imageomics/bioclip-2")
    tok = open_clip.get_tokenizer("hf-hub:imageomics/bioclip-2")
    model.eval()
    templates = ["a photo of {}.", "a photo of {}, a type of organism."]
    embs = []
    texts = [taxon_string(t) for t in taxa]
    with torch.no_grad():
        for i in range(0, len(texts), 256):
            chunk = texts[i:i + 256]
            acc = None
            for tp in templates:
                e = model.encode_text(tok([tp.format(x) for x in chunk]))
                e = torch.nn.functional.normalize(e, dim=-1)
                acc = e if acc is None else acc + e
            embs.append(torch.nn.functional.normalize(acc, dim=-1).numpy())
            print("text", i + len(chunk), "/", len(texts), flush=True)
    T = np.concatenate(embs).astype(np.float16)
    np.save(f"{OUT}/text_emb.npy", T)
    json.dump([{k: t.get(k) for k in ("key", "species", *RANKS, "vernacular", "n_kz", "redbook")} for t in taxa],
              open(f"{OUT}/species.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # ---- визуальная часть -> ONNX int8 ----
    tf = preprocess.transforms
    size = 224
    mean, std = (0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)
    for x in tf:
        if x.__class__.__name__ == "Normalize":
            mean, std = tuple(map(float, x.mean)), tuple(map(float, x.std))
        if x.__class__.__name__ == "CenterCrop":
            size = int(x.size[0] if isinstance(x.size, (list, tuple)) else x.size)
    cfg = {"size": size, "mean": mean, "std": std, "logit_scale": 100.0, "model": "imageomics/bioclip-2",
           "n_species": len(taxa), "built": time.strftime("%Y-%m-%d")}
    json.dump(cfg, open(f"{OUT}/config.json", "w"), indent=1)

    class Vis(torch.nn.Module):
        def __init__(self, v):
            super().__init__()
            self.v = v

        def forward(self, x):
            return torch.nn.functional.normalize(self.v(x), dim=-1)

    vis = Vis(model.visual).eval()
    torch.onnx.export(vis, torch.randn(1, 3, size, size), "visual_fp32.onnx", input_names=["image"],
                      output_names=["emb"], dynamic_axes={"image": {0: "b"}, "emb": {0: "b"}}, opset_version=17,
                      dynamo=False)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic("visual_fp32.onnx", "bioclip2_visual_int8.onnx", weight_type=QuantType.QInt8)
    print("onnx int8 MB:", os.path.getsize("bioclip2_visual_int8.onnx") / 1e6, flush=True)

    # ---- проверка точности на реальных фото ----
    import onnxruntime as ort
    sess = ort.InferenceSession("bioclip2_visual_int8.onnx", providers=["CPUExecutionProvider"])
    Tf = T.astype(np.float32)

    def prep(img):
        img = img.convert("RGB")
        w, h = img.size
        s = size / min(w, h)
        img = img.resize((max(size, round(w * s)), max(size, round(h * s))), Image.BICUBIC)
        w, h = img.size
        l, t = (w - size) // 2, (h - size) // 2
        a = np.asarray(img.crop((l, t, l + size, t + size)), dtype=np.float32) / 255.0
        a = (a - np.array(mean, np.float32)) / np.array(std, np.float32)
        return a.transpose(2, 0, 1)[None]

    def photo(t):
        j = get(f"{GBIF}/occurrence/search", taxonKey=t["key"], mediaType="StillImage",
                basisOfRecord="HUMAN_OBSERVATION", year="2025,2026", limit=5)  # свежие фото — их не было в обучении
        for o in (j or {}).get("results", []):
            for m in o.get("media", []):
                u = m.get("identifier")
                if u and m.get("type") == "StillImage":
                    try:
                        r = S.get(u, timeout=30)
                        if r.ok:
                            return Image.open(io.BytesIO(r.content))
                    except Exception:
                        pass
        return None

    random.seed(7)
    res = {}
    groups = {"Plantae": [t for t in taxa if t["kingdom"] == "Plantae"],
              "Animalia": [t for t in taxa if t["kingdom"] == "Animalia"],
              "Red Book": [t for t in taxa if t["redbook"]]}
    idx = {t["species"]: i for i, t in enumerate(taxa)}
    for g, lst in groups.items():
        sample = random.sample(lst, min(len(lst), 120))
        with ThreadPoolExecutor(12) as ex:
            imgs = list(ex.map(photo, sample))
        top1 = top5 = n = 0
        gen1 = 0
        for t, im in zip(sample, imgs):
            if im is None:
                continue
            try:
                e = sess.run(None, {"image": prep(im)})[0][0]
            except Exception:
                continue
            order = np.argsort(-(Tf @ e))[:5]
            n += 1
            top1 += int(order[0] == idx[t["species"]])
            top5 += int(idx[t["species"]] in order)
            gen1 += int(taxa[order[0]]["genus"] == t["genus"])
        res[g] = {"n": n, "top1": round(100 * top1 / max(n, 1), 1), "top5": round(100 * top5 / max(n, 1), 1),
                  "genus_top1": round(100 * gen1 / max(n, 1), 1)}
        print(g, res[g], flush=True)
    json.dump({"accuracy": res, **cfg}, open(f"{OUT}/report.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
