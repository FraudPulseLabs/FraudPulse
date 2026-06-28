# FraudPulse RAG Assistant

A self-contained **Retrieval-Augmented Generation (RAG)** subsystem that powers
the public landing-page assistant. It answers visitor questions **strictly from
a curated corpus** of FraudPulse product documentation and **refuses anything
outside that corpus**, so it never hallucinates product claims.

```
load docs → chunk → embed → store (FAISS) → retrieve → generate (Groq) → validate → cite
```

---

## 1. Where to put your API key (read this first)

The only secret this subsystem needs is a **Groq API key**, used for answer
generation.

1. Create a free key at <https://console.groq.com/keys>.
2. Copy the backend env template and add your key:

   ```bash
   cd backend
   cp .env.example .env      # if you don't already have a .env
   ```

3. Edit `backend/.env` and set:

   ```env
   GROQ_API_KEY=gsk_your_real_key_here
   ```

`backend/.env` is **git-ignored** — never commit your key.

The key is read in [`rag/config.py`](./config.py) via
`os.getenv("GROQ_API_KEY")`. You can also override the model with
`GROQ_MODEL` and the embedding model with `EMBEDDING_MODEL` in the same file.

| Where | Variable | How |
| --- | --- | --- |
| Local dev | `GROQ_API_KEY` | `backend/.env` |
| Render | `GROQ_API_KEY` | Dashboard → Environment (`render.yaml` declares it `sync: false`) |
| OCI deploy | `GROQ_API_KEY` | GitHub Actions repository secret (injected by the deploy workflow) |

> Without a key, **retrieval still works** but generation is disabled and the
> assistant returns a "temporarily unavailable" message. Refusal of
> out-of-corpus questions also still works (it happens before any LLM call).

---

## 2. Layout

```
backend/rag/
├── config.py                 # ALL settings: paths, RANDOM_SEED, models,
│                             #   CHUNK_SIZE/OVERLAP, TOP_K, SYSTEM_PROMPT
├── docs/                     # the corpus (.md / .txt / .html / .pdf)
├── index/                    # built vector store (faiss.index + chunks.json)
├── eval/                     # qa_pairs.json + results.json
├── app/
│   ├── document_loader.py    # files → cleaned Document objects (+ metadata)
│   ├── chunking.py           # Document → Chunk objects (hybrid strategy)
│   ├── embeddings.py         # sentence-transformers MiniLM wrapper
│   ├── vector_store.py       # FAISS IndexFlatIP (cosine) add/search/save/load
│   ├── prompts.py            # context formatting + citation sources
│   ├── rag_system.py         # retrieve → generate → validate → cite
│   └── evaluation.py         # groundedness / citation accuracy / latency
├── scripts/
│   ├── build_vector_db.py    # load → chunk → embed → save
│   └── evaluate.py           # run the evaluation suite
└── README.md                 # this file
```

---

## 3. Configuration (`config.py`)

Everything tunable lives in one place:

| Setting | Default | Meaning |
| --- | --- | --- |
| `RANDOM_SEED` | `42` | Determinism across chunking/embedding |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Generation model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local embedding model (384-dim) |
| `CHUNK_SIZE` | `1000` | Target characters per chunk |
| `CHUNK_OVERLAP` | `200` | Sliding-window overlap |
| `TOP_K` | `5` | Chunks retrieved per query |
| `MIN_RELEVANCE_SCORE` | `0.25` | Cosine floor; below this → refuse |
| `SYSTEM_PROMPT` | — | Constrains the LLM to the context |

---

## 4. The corpus (`docs/`)

The corpus is plain documentation about FraudPulse. To change the assistant's
knowledge, **edit or replace the files in `docs/`** and rebuild the index.

- Supported formats: `.md`, `.txt`, `.html`/`.htm`, `.pdf`.
- Markdown headings (`#`, `##`, …) are used by the chunker to keep sections
  coherent, so well-structured Markdown gives the best retrieval.
- After any change to `docs/`, **rebuild** (section 6).

---

## 5. Install dependencies

The heavy ML deps are kept in a separate file so the core backend stays light:

```bash
cd backend
pip install -r requirements.txt -r requirements-rag.txt
```

`requirements-rag.txt` pulls `sentence-transformers` (+ torch), `faiss-cpu`,
`groq`, and `pypdf`. Python 3.11/3.12 is recommended (torch wheels).

---

## 6. Build the index

Run the offline pipeline once (and after any corpus change):

```bash
cd backend
python -m rag.scripts.build_vector_db
```

This loads `docs/`, chunks, embeds with MiniLM, and writes the FAISS index and
chunk sidecar to `rag/index/`. The first run downloads the embedding model
(~80 MB) from Hugging Face.

---

## 7. Run / use the assistant

The assistant is served by the FastAPI backend as a **public** endpoint:

```
POST /api/v1/assistant/chat
{ "message": "How does scoring work?" }
```

Response:

```jsonc
{
  "answer": "FraudPulse scores each transaction ... [1][2]",
  "sources": [{ "number": 1, "title": "Scoring Methodology", "filename": "02-scoring-methodology.md", ... }],
  "grounded": true,
  "refused": false,
  "latency_ms": 740.2,
  "model": "llama-3.3-70b-versatile"
}
```

Start the backend locally:

```bash
cd backend
python run.py        # http://localhost:8000  (Swagger at /docs)
```

The Angular landing-page chatbot widget calls this endpoint
(`frontend/.../core/services/chatbot.service.ts`). All knowledge now lives in
the backend corpus — the old client-side `chatbot-knowledge.ts` was removed.

You can also call it programmatically:

```python
from rag.app.rag_system import get_rag_system
print(get_rag_system().answer("What is FraudPulse?").answer)
```

---

## 8. How it works (pipeline)

1. **Load** (`document_loader.py`) — read files, strip HTML/PDF noise, normalise
   whitespace, derive `title` / `filename` / `word_count`.
2. **Chunk** (`chunking.py`) — **hybrid**: split on Markdown headings first, then
   apply a sliding window (`CHUNK_SIZE`/`CHUNK_OVERLAP`) to any oversized
   section, breaking on sentence/word boundaries. Deterministic (seeded).
3. **Embed** (`embeddings.py`) — `all-MiniLM-L6-v2`, **L2-normalized** so dot
   product = cosine similarity. Runs locally on CPU.
4. **Store** (`vector_store.py`) — FAISS `IndexFlatIP`; `add` / `search` /
   `save` / `load`.
5. **Retrieve** (`rag_system.py`) — embed the query, fetch `TOP_K`. If the best
   score `< MIN_RELEVANCE_SCORE`, **refuse** (no LLM call).
6. **Generate** — Groq LLM with the `SYSTEM_PROMPT` + numbered context.
7. **Validate + cite** — confirm the answer cites at least one retrieved source;
   detect explicit "no information" refusals; return the cited sources.

---

## 9. Evaluation

```bash
cd backend
python -m rag.scripts.evaluate          # human-readable report
python -m rag.scripts.evaluate --json   # full JSON
```

Metrics (written to `rag/eval/results.json`):

- **Groundedness** — share of in-corpus answers that cite a valid source.
- **Citation accuracy** — answers that cite the expected source document.
- **Keyword recall** — expected key facts present in the answer.
- **Out-of-corpus refusal accuracy** — off-topic questions correctly refused.
- **Latency** — mean / p50 / p95 / max per query.

Edit `rag/eval/qa_pairs.json` to extend the test set. Generation metrics need
`GROQ_API_KEY`; retrieval/refusal metrics run without it.

---

## 10. Deployment

- **Docker** (`backend/Dockerfile`) installs both requirements files,
  **pre-caches the embedding model**, and `COPY`s `rag/` (including the prebuilt
  `index/`), so the container needs no network for embeddings at runtime.
- **Render** (`render.yaml`) declares a Docker backend service with
  `GROQ_API_KEY` as a dashboard secret.
- **OCI** (`.github/workflows/deploy.yml`) injects `GROQ_API_KEY` into the
  server `.env`.
- **CI** (`.github/workflows/ci.yml`) has a `rag-index` job that builds the
  index and runs a retrieval + refusal smoke test on every PR.
- **Procfile** provides a `web` process and a `release` step that rebuilds the
  index on platforms that support it.

---

## 11. Troubleshooting

| Symptom | Fix |
| --- | --- |
| **`503 Service Unavailable` + `No module named 'sentence_transformers'`** | You started the server with an interpreter that lacks the RAG extras. Run it with the venv that has them (see below). |
| `Vector store not found` | Run `python -m rag.scripts.build_vector_db`. |
| `GROQ_API_KEY is not set` | Add it to `backend/.env` (section 1). |
| Assistant refuses a valid question | Lower `MIN_RELEVANCE_SCORE` or add the topic to `docs/` and rebuild. |
| `No matching distribution` for torch | Use Python 3.11/3.12 (torch has no wheels for 3.14). |
| Answers feel stale after editing docs | Rebuild the index. |

### Use a Python 3.11/3.12 virtualenv

The RAG extras (torch via `sentence-transformers`) **cannot install on Python
3.14**, so the project uses a single Python 3.11/3.12 virtualenv at
`backend/.venv`. The system `python` (3.14) can import FastAPI but not the RAG
deps, which is what causes the `503`. Always run the backend through this venv:

```bash
cd backend
.venv/bin/python run.py
# or: source .venv/bin/activate && python run.py
```

To recreate the environment from scratch:

```bash
cd backend
python3.11 -m venv .venv            # or python3.12
.venv/bin/pip install --upgrade pip
# CPU-only torch first to avoid the large CUDA packages:
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements.txt -r requirements-rag.txt
.venv/bin/python -m rag.scripts.build_vector_db
```
