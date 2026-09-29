"""Índice híbrido (BM25 + embeddings multilingües) sobre las Condiciones Generales
del PPR OptiMaxx plus Art. 151 (Allianz México).

Uso:
    python rag.py build              # construye index/ desde la CG identificada abajo
    python rag.py search "query" -k 6
    python rag.py show <chunk_id>    # texto completo de un chunk

Chunking: una sección numerada = un chunk (2.2, 3.14.1, ...). Los encabezados sin
número ("Monto:", "a) Beneficiario Irrevocable") se quedan como texto dentro de su
sección. Las secciones mayores que MAX_CHARS se parten por párrafos. El índice (TOC)
se marca como navegacional y queda fuera de la recuperación.
"""
import argparse
import hashlib
import json
import pickle
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent.parent   # raíz del proyecto
MD_PATH = BASE / "data" / "processed" / "CG-OptiMaxx-plus-Art.151-CNSF-S0003-0247-2018.md"
INDEX_DIR = BASE / "index"
DOC_ID = "CG-OptiMaxx-plus-Art.151"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ALPHA = 0.65        # peso de BM25 en la mezcla híbrida
MAX_CHARS = 3500

SEC_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+(.*)$")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    # prefijo de 6 caracteres como stemmer de truncamiento para español:
    # iguala "interrumpo"/"interrupción" o "aportaciones"/"aportación"
    return [t[:6] for t in TOKEN_RE.findall(strip_accents(text).lower())]


# ---------------------------------------------------------------- chunking

def parse_chunks(md_text: str) -> list[dict]:
    lines = md_text.splitlines()
    chunks: list[dict] = []
    titles: dict[str, str] = {}          # "3.14" -> "Retiros totales y parciales"
    cur: dict | None = None              # sección numerada en curso

    def flush():
        nonlocal cur
        if cur is None:
            return
        body = "\n".join(cur.pop("_body")).strip()
        if body:
            cur["text"] = body
            chunks.append(cur)
        cur = None

    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            heading = m.group(2).strip()
            sec = SEC_RE.match(heading)
            if sec:
                flush()
                num, title = sec.group(1), sec.group(2).strip()
                titles[num] = title
                path = " > ".join(
                    f"{n}. {titles[n]}" for n in ancestors(num) if n in titles
                )
                cur = {
                    "id": None,  # se asigna al final
                    "doc": DOC_ID,
                    "section": num,
                    "title": title,
                    "path": path or f"{num}. {title}",
                    "navigational": title.lower() == "índice",
                    "_body": [],
                }
            elif cur is not None:
                # encabezado sin número: texto dentro de la sección en curso
                cur["_body"].append(f"**{heading}**")
            continue
        if cur is not None:
            cur["_body"].append(line)
    flush()

    # partir secciones muy grandes por párrafos
    out: list[dict] = []
    for c in chunks:
        if len(c["text"]) <= MAX_CHARS or c["navigational"]:
            out.append(c)
            continue
        paras = re.split(r"\n\s*\n", c["text"])
        buf, part = [], 1
        for p in paras:
            if sum(len(x) for x in buf) + len(p) > MAX_CHARS and buf:
                out.append({**c, "part": part, "text": "\n\n".join(buf)})
                buf, part = buf[-1:], part + 1   # solape de un párrafo
            buf.append(p)
        if buf:
            out.append({**c, "part": part, "text": "\n\n".join(buf)})
    for i, c in enumerate(out):
        c["id"] = i
        # dos textos indexados: el boost de título (ruta x3) solo para BM25;
        # el embedding usa texto limpio porque la repetición diluye la semántica
        c["index_text"] = (c["path"] + "\n") * 3 + c["text"]
        c["embed_text"] = c["path"] + "\n" + c["text"]
    return out


def ancestors(num: str) -> list[str]:
    parts = num.split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


# ---------------------------------------------------------------- build

def build():
    from rank_bm25 import BM25Okapi

    source = MD_PATH.read_bytes()
    source_sha256 = hashlib.sha256(source).hexdigest()
    chunks = parse_chunks(source.decode("utf-8"))
    INDEX_DIR.mkdir(exist_ok=True)

    (INDEX_DIR / "chunks.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks), encoding="utf-8"
    )

    retrievable = [c for c in chunks if not c["navigational"]]
    bm25 = BM25Okapi([tokenize(c["index_text"]) for c in retrievable], k1=1.2, b=0.75)
    with open(INDEX_DIR / "bm25.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "retrievable_ids": [c["id"] for c in retrievable]}, f)

    from fastembed import TextEmbedding
    model = TextEmbedding(MODEL_NAME)
    embs = np.vstack(list(model.embed([c["embed_text"] for c in chunks]))).astype(np.float32)
    embs /= np.linalg.norm(embs, axis=1, keepdims=True)
    np.save(INDEX_DIR / "embeddings.npy", embs)

    (INDEX_DIR / "meta.json").write_text(
        json.dumps(
            {
                "model": MODEL_NAME,
                "source": str(MD_PATH.relative_to(BASE)).replace("\\", "/"),
                "source_sha256": source_sha256,
                "dim": int(embs.shape[1]),
                "n_chunks": len(chunks),
                "n_retrievable": len(retrievable),
                "excluded": [c["path"] for c in chunks if c["navigational"]],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"OK: {len(chunks)} chunks ({len(retrievable)} recuperables) -> {INDEX_DIR}")


# ---------------------------------------------------------------- search

def load():
    meta_path = INDEX_DIR / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError("Falta el índice RAG: ejecuta 'python src/rag.py build'")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    current_source = str(MD_PATH.relative_to(BASE)).replace("\\", "/")
    current_hash = hashlib.sha256(MD_PATH.read_bytes()).hexdigest()
    if (meta.get("source") != current_source or meta.get("source_sha256") != current_hash
            or meta.get("model") != MODEL_NAME):
        raise RuntimeError("El índice RAG no corresponde a la CG actual: ejecuta 'python src/rag.py build'")
    chunks = [
        json.loads(l)
        for l in (INDEX_DIR / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    with open(INDEX_DIR / "bm25.pkl", "rb") as f:
        bm = pickle.load(f)
    embs = np.load(INDEX_DIR / "embeddings.npy")
    if len(chunks) != meta["n_chunks"] or embs.shape != (meta["n_chunks"], meta["dim"]):
        raise RuntimeError("El índice RAG está incompleto: ejecuta 'python src/rag.py build'")
    return chunks, bm, embs


_model = None


def embed_query(q: str) -> np.ndarray:
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(MODEL_NAME)
    v = np.array(next(_model.embed([q])), dtype=np.float32)
    v /= np.linalg.norm(v)
    return v


def fuse(bm25_scores: np.ndarray, dense_scores: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    """Mezcla de scores normalizados: alpha*bm25 + (1-alpha)*dense.

    Elegida por evaluación sobre 10 consultas con respuesta conocida: 9/10 top-1
    (vs 5/10 de RRF y 8/10 de BM25 solo). BM25 domina porque en este corpus legal
    la evidencia léxica exacta casi siempre señala la sección correcta; el denso
    cubre paráfrasis donde BM25 falla.
    """
    b = bm25_scores / bm25_scores.max() if bm25_scores.max() > 1e-6 else None
    d = dense_scores / dense_scores.max() if dense_scores.max() > 1e-6 else None
    if b is None and d is None:
        return bm25_scores * 0.0
    if b is None:
        return d
    if d is None:
        return b
    return alpha * b + (1 - alpha) * d


def search(query: str, k: int = 6):
    chunks, bm, embs = load()
    bm25, rids = bm["bm25"], bm["retrievable_ids"]

    bm25_scores = bm25.get_scores(tokenize(query))
    dense_scores = embs[rids] @ embed_query(query)
    fused_scores = fuse(bm25_scores, dense_scores)
    order = sorted(range(len(rids)), key=lambda i: -fused_scores[i])

    for i in order[:k]:
        c = chunks[rids[i]]
        part = f" (parte {c['part']})" if c.get("part") else ""
        snippet = re.sub(r"\s+", " ", c["text"])[:280]
        print(f"[{c['id']:>3}] {c['path']}{part}")
        print(f"      fused={fused_scores[i]:.4f} bm25={bm25_scores[i]:.2f} dense={dense_scores[i]:.3f}")
        print(f"      {snippet}")
        print()


def show(chunk_id: int):
    chunks, _, _ = load()
    c = chunks[chunk_id]
    print(f"### {c['path']}\n")
    print(c["text"])


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=6)
    sh = sub.add_parser("show")
    sh.add_argument("id", type=int)
    args = ap.parse_args()
    if args.cmd == "build":
        build()
    elif args.cmd == "search":
        search(args.query, args.k)
    else:
        show(args.id)
