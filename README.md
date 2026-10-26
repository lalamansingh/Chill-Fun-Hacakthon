# TruthLens — AI-Based Image Authenticity Verification, Deepfake Detection & Intelligent Content Restoration System

TruthLens is a full-stack web application that helps journalists, investigators, educators and everyday
users decide whether an image can be trusted. A signed-in user uploads a JPEG, PNG or WebP image and gets a
verdict (**authentic**, **manipulated**, **deepfake** or **AI-generated**) with a 0–100 authenticity score.
The score combines classical forensics (metadata, Error Level Analysis, noise and frequency analysis) with
deep-learning detectors for face deepfakes and AI-generated images. Every result comes with an explanation:
a heatmap, boxes around suspicious regions, a plain-English summary and an uncertainty note. Users can
optionally restore tampered regions with AI (the output is clearly labelled *AI-RECONSTRUCTED*), download a
PDF forensic report, and look back over their history and a dashboard of past analyses.

> **Responsible AI:** TruthLens verdicts are *Probabilistic evidence, corroborated by human review — never a
> substitute for it.*

---

## Features

- **Multi-signal authenticity analysis**: EXIF/metadata inspection, Error Level Analysis (ELA), noise-residual
  and frequency-domain analysis, plus deep-learning deepfake and AI-generated-image detectors.
- **Four-way verdict** (authentic / manipulated / deepfake / ai_generated), a 0–100 authenticity score and a
  confidence value.
- **Explainability**: heatmap overlay, ELA image, suspicious-region and face boxes, a score for each signal
  with an explanation, and an uncertainty note.
- **Intelligent content restoration**: inpaints suspicious regions (automatically or from user-drawn
  boxes/masks). The output is watermarked *AI-RECONSTRUCTED* and is never presented as original evidence.
- **PDF forensic report** for each analysis, generated on demand and cached.
- **Accounts & privacy**: JWT authentication and per-user data isolation. Users only ever see their own data.
- **History & dashboard**: search and filter past analyses, see totals by verdict, a 7-day trend and recent
  activity.
- **Graceful degradation**: `ML_ENABLE_DEEP=false` runs the classical forensics only (fast, no PyTorch
  needed). A model that is unavailable is excluded from the weighting rather than failing the request.
- **Production-ready packaging**: Docker Compose (PostgreSQL + FastAPI + nginx), non-root containers,
  health checks, GitHub Actions CI.

## Architecture

```mermaid
flowchart LR
    U[User / Browser] -->|HTTPS| N

    subgraph FE["frontend container"]
        N[nginx<br/>SPA static files<br/>/api reverse proxy]
    end

    subgraph BE["backend container"]
        A[FastAPI<br/>auth · images · analyses<br/>history · reports]
        P[ML pipeline<br/>app/ml/pipeline.py]
        A -->|threadpool| P
        P --> C1[Classical forensics<br/>metadata · ELA · noise · frequency]
        P --> C2[Deep models<br/>deepfake · AI-generated<br/>PyTorch / Hugging Face]
        P --> R[Restoration<br/>inpainting]
    end

    N -->|/api/*| A
    A --> DB[(PostgreSQL)]
    A --> FS[[File storage<br/>uploads · heatmaps<br/>restored · reports]]
    C2 -.weights.-> MC[[models_cache volume]]
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the request lifecycle, the ER diagram, the ML stages and
security notes.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, React Router, Recharts, Axios, lucide-react |
| Web server | nginx (SPA hosting, gzip, `/api` reverse proxy) |
| Backend API | Python 3.12, FastAPI, Uvicorn, Pydantic v2, python-jose (JWT), bcrypt |
| Database | PostgreSQL 16 (production) / SQLite (local dev), SQLAlchemy 2.0, Alembic |
| ML / forensics | PyTorch (CPU), Hugging Face Transformers, OpenCV, NumPy, SciPy, Pillow |
| Reports | ReportLab (PDF) |
| DevOps | Docker, Docker Compose, GitHub Actions, Make |

## Quick start (Docker, recommended)

Requirements: Docker with Compose v2. Allow at least 4 GB of RAM for the containers, because the ML models
are loaded into memory.

```bash
cp .env.example .env          # optional: edit SECRET_KEY etc.
docker compose up --build
```

Open **http://localhost:8080**, register an account and upload an image.

- API docs (Swagger UI): http://localhost:8000/docs (also proxied at http://localhost:8080/docs)
- The first build downloads the model weights into the image (`PRELOAD_MODELS=true`). For a quicker build,
  set `PRELOAD_MODELS=false` and the weights download on the first analysis instead.
- Data lives in the named volumes `pgdata`, `storage` and `models_cache`. Stop the stack with
  `docker compose down`, or delete everything with `docker compose down -v`.

Shortcuts: `make up`, `make logs`, `make down`, `make build`.

## Local development (without Docker)

Requirements: Python 3.12 (with [uv](https://docs.astral.sh/uv/) recommended) and Node.js 20. The backend
uses **SQLite by default**, so no database setup is needed.

```bash
make setup          # backend/.venv + pip deps, frontend npm install
make dev            # backend on :8000 (auto-reload) + Vite on :5173
```

Open **http://localhost:5173**. Vite proxies `/api` to `http://localhost:8000`.

Manual equivalent:

```bash
# backend
cd backend
uv venv .venv --python 3.12            # or: python3 -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Useful options:

- `ML_ENABLE_DEEP=false make dev-backend` runs classical forensics only (fast, no model downloads).
- `make models` pre-downloads the model weights into `MODEL_CACHE_DIR`.
- `make db-up` starts only PostgreSQL in Docker. Then
  `export DATABASE_URL=postgresql+psycopg://truthlens:truthlens@localhost:5432/truthlens`.
- On Linux, install CPU-only PyTorch with `--extra-index-url https://download.pytorch.org/whl/cpu` (the
  Makefile does this for you).

All configuration options are listed in [.env.example](.env.example).

## API overview

All endpoints are under `/api` and return JSON. Errors look like `{"detail": "..."}`. Authentication uses
`Authorization: Bearer <jwt>`. Endpoints that return files (📎) also accept `?token=<jwt>`. You can try the
API interactively at **http://localhost:8000/docs**.

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Service status, deep-ML enabled, models loaded |
| POST | `/api/auth/register` | Create account → JWT |
| POST | `/api/auth/login` | Log in → JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/images` | Upload image (multipart field `file`, JPEG/PNG/WebP, ≤ 10 MB) |
| GET | `/api/images` | List my images (newest first) |
| GET | `/api/images/{id}` | Image metadata |
| GET 📎 | `/api/images/{id}/file` | Original image bytes |
| DELETE | `/api/images/{id}` | Delete image, its files and analyses |
| POST | `/api/analyses` | Run the forensic pipeline on `{image_id}` |
| GET | `/api/analyses/{id}` | Analysis result |
| GET 📎 | `/api/analyses/{id}/heatmap` | Explainability heatmap (PNG) |
| GET 📎 | `/api/analyses/{id}/ela` | Error Level Analysis image (PNG) |
| POST | `/api/analyses/{id}/restore` | AI restoration (optional `boxes` / `mask_base64`) |
| GET 📎 | `/api/restorations/{id}/file` | Restored image (PNG, labelled AI-RECONSTRUCTED) |
| GET 📎 | `/api/reports/{analysis_id}/pdf` | PDF forensic report |
| GET | `/api/history` | Paginated history (`q`, `verdict`, `page`, `page_size`) |
| GET | `/api/dashboard/stats` | Totals, verdict breakdown, 7-day trend, recent items |

The full schema contract is in [docs/CONTRACT.md](docs/CONTRACT.md).

## Project structure

```
Chill-Fun-Hacakthon/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory, routers, startup warm-up
│   │   ├── config.py          # env-driven settings
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── models/            # ORM tables
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── routes/            # REST endpoints
│   │   ├── services/          # storage, security, PDF reports, ML bridge
│   │   └── ml/                # forensic + deep-learning pipeline (pipeline.py entry point)
│   ├── alembic/ alembic.ini   # database migrations
│   ├── scripts/download_models.py
│   ├── tests/                 # pytest suite (tests/ml for the pipeline)
│   ├── requirements.txt       # includes -r requirements-ml.txt
│   ├── docker/entrypoint.sh   # wait-for-db → migrate → uvicorn
│   └── Dockerfile
├── frontend/
│   ├── src/                   # React app (pages, components, api client)
│   ├── nginx.conf             # SPA + /api proxy config for the container
│   └── Dockerfile
├── docs/                      # CONTRACT.md, ARCHITECTURE.md, DEPLOYMENT.md
├── .github/workflows/ci.yml   # backend tests, frontend build/lint, docker builds
├── docker-compose.yml         # full stack
├── docker-compose.dev.yml     # PostgreSQL only, for local dev
├── Makefile
└── .env.example
```

## Testing

```bash
make test                     # backend pytest, ML_ENABLE_DEEP=false (fast)
make test-ml                  # same with the deep models enabled (slow, needs weights)
make lint                     # frontend ESLint
cd frontend && npm run build  # production build check
```

On every push to `main` and on every pull request, CI runs the backend tests (CPU-only torch, classical ML
mode), lints and builds the frontend, and builds both Docker images. See
[.github/workflows/ci.yml](.github/workflows/ci.yml).

## ML models & credits

| Purpose | Model | Licence |
|---|---|---|
| Face deepfake detection | [`prithivMLmods/deepfake-detector-model-v1`](https://huggingface.co/prithivMLmods/deepfake-detector-model-v1) (SigLIP-base, 224 px) | Apache-2.0 |
| AI-generated image detection | [`haywoodsloan/ai-image-detector-deploy`](https://huggingface.co/haywoodsloan/ai-image-detector-deploy) (SwinV2, 256 px) | Apache-2.0 |
| Face detection | OpenCV YuNet (`face_detection_yunet_2023mar.onnx`), Haar cascade fallback | MIT / BSD (OpenCV Zoo) |

Swap either detector with the `ML_DEEPFAKE_MODEL` / `ML_AIGEN_MODEL` env vars. The model in use is
reported in each analysis under `result.model_versions`. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Team

**GL Bajaj Institute of Technology & Management, Greater Noida** · Department of Computer Science &
Engineering · Session 2026–27

| Name | Roll No. | Role |
|---|---|---|
| Prince Tomar | 2401920100244 | Team Leader |
| Sachin Kumar | 2401920100276 | Member |
| Piyush Kumar | 2401920100230 | Member |
| Priyanshu Kumar | 2401920100248 | Member |

**Project Guide:** Mr. Prasanna Dwivedi

## Responsible-AI disclaimer

Image forensics is an adversarial, fast-moving field. No detector is perfect: new generators, heavy
compression, resizing and screenshots can all produce false positives and false negatives. TruthLens reports
calibrated *likelihoods*, explains which signals drove each verdict, and states its uncertainty openly.
AI-restored images are watermarked and must never be used as evidence of what the original showed.

**Probabilistic evidence, corroborated by human review — never a substitute for it.**

## Future scope

- **Video & audio deepfake detection**: frame-level and temporal consistency analysis, and voice-clone
  detection.
- **Mobile app & browser extension**: verify images directly in social feeds and messaging apps.
- **Platform API**: authenticated public API and webhooks for newsrooms and moderation pipelines.
- **C2PA / Content Credentials provenance**: read and verify signed provenance manifests.
- **Continuous learning**: retrain on user-confirmed (human-reviewed) cases to keep up with new generators.
- **Blockchain chain-of-custody**: tamper-evident anchoring of image hashes and reports for legal use.
