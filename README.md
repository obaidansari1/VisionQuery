# VisionQuery

Search inside a video for a moment, described in plain English — "person picks up a bag",
"car turns left" — and jump straight to it.

## How it works

1. **Upload** — a video is uploaded and a Celery task is queued to process it.
2. **Sample** — the worker reads the video with OpenCV at a fixed rate (5 FPS by default) for
   even coverage, and adds denser motion-triggered sampling (10 FPS) during short windows where
   something visibly changes, so brief events aren't missed between fixed samples.
3. **Embed** — every sampled frame is saved as a JPEG thumbnail and embedded with a CLIP model
   (`clip-ViT-B-32`) into a 512-dimensional vector, then stored in PostgreSQL via `pgvector`.
4. **Search** — a text query is embedded with the *same* CLIP model (images and text share one
   vector space), then compared against every stored frame with cosine similarity. The closest
   matches come back ranked, each with its timestamp and thumbnail.

A single-page UI (served by Django itself, no separate frontend build) ties this together:
upload a clip, watch it process, type a query, click a result to jump the video player there.

## What is included

- Django + Django REST Framework API in `backend/`
- A built-in demo UI at `/` (upload, status polling, event search, results grid)
- PostgreSQL with the `pgvector` extension, storing per-frame CLIP embeddings with an HNSW index
- Celery with Redis as both broker and result backend
- `VideoUpload` records with `pending`, `processing`, `done`, and `failed` status
- `Frame` records: one per sampled frame, with its thumbnail image, timestamp, sample type
  (`fixed` or `active`), and CLIP embedding
- A Django admin view (`/admin/`) with an inline thumbnail gallery per video, useful for
  showing exactly which frames were sampled and embedded

## Prerequisites

- Python 3.11+ recommended
- Docker Desktop (for PostgreSQL + Redis), or local PostgreSQL with the `vector` extension
  installed and Redis
- ~2 GB free disk and an internet connection the first time you run the worker, to download the
  CLIP model weights (cached afterwards, no internet needed on later runs)

## Start PostgreSQL and Redis

From the repository root:

```powershell
docker compose up -d
docker compose ps
```

This starts PostgreSQL on `localhost:5432` and Redis on `localhost:6379`. PostgreSQL uses
database/user/password `visionquery`.

The database container enables `vector` on first initialization. The Django migration also uses
`CREATE EXTENSION IF NOT EXISTS vector`, so the extension is enabled when migrations run against
a local pgvector-enabled PostgreSQL instance.

## Install the Django backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
```

`requirements.txt` now also installs `sentence-transformers` (CLIP model + inference),
`Pillow` (thumbnail encoding) and `python-dotenv` (already used by `settings.py`, previously
missing from the file).

When using the repository's Docker Compose services, make sure the Django process uses the same
database credentials as Compose. Environment variables override any values in `backend/.env`:

```powershell
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "visionquery"
$env:POSTGRES_USER = "visionquery"
$env:POSTGRES_PASSWORD = "visionquery"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
```

Optionally create an admin login, to browse sampled frames in `/admin/`:

```powershell
python manage.py createsuperuser
```

## Run Django and Celery

Use two terminals, each with the virtual environment activated and working directory set to
`backend`.

Terminal 1:

```powershell
python manage.py runserver
```

Terminal 2:

```powershell
celery -A VisionQuery worker --loglevel=INFO --pool=solo
```

The first time the worker processes a video, it downloads the CLIP model weights
(~600 MB, one-time, requires internet). If you're demoing offline, run the worker on one clip
ahead of time so the weights are cached before the live demo.

## Try it: the demo UI

Open **http://127.0.0.1:8000/** in a browser. From there you can:

1. Upload a short clip (10–30 seconds works best for a snappy live demo on CPU).
2. Watch the status badge move from `pending` → `processing` → `done`.
3. Type a plain-English description of a moment in the video and hit Search.
4. Click any result thumbnail to jump the video player to that timestamp.

`/admin/` (after `createsuperuser`) shows every `VideoUpload` with an inline gallery of its
sampled frames — a good way to visually show off the fixed-vs-adaptive sampling during a viva.

## Try it: the raw API

Upload a file (PowerShell `curl` is an alias, so use `curl.exe`):

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/upload/ -F "file=@C:\path\to\video.mp4"
```

The response returns immediately:

```json
{"video_id": 1}
```

Poll its state:

```powershell
curl.exe http://127.0.0.1:8000/api/status/1/
```

Initially the response has `"status":"pending"`, then `"processing"` while the worker reads and
embeds frames, then:

```json
{"video_id":1,"status":"done","uploaded_at":"...","file_url":"...","frame_count":143}
```

List uploaded videos:

```powershell
curl.exe http://127.0.0.1:8000/api/videos/
```

Search a processed video by event, once its status is `done`:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/search/ `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"person picks up a bag\", \"video_id\": 1, \"top_k\": 5}'
```

```json
{
  "query": "person picks up a bag",
  "video_id": 1,
  "results": [
    {
      "video_id": 1,
      "frame_number": 214,
      "timestamp_seconds": 8.56,
      "sample_type": "active",
      "image_url": "http://127.0.0.1:8000/media/frame_thumbnails/.../video1_frame214.jpg",
      "score": 0.31
    }
  ]
}
```

`score` is `1 - cosine distance`, so higher means a closer match. `video_id` is optional in the
request; omit it to search across every processed video.

The Celery worker logs source FPS, frame count, duration, motion windows, and how many frames
were embedded and saved. For a 30 FPS source video, fixed sampling selects frames 0, 6, 12, and
so on; active sampling selects roughly 10 frames per second only around detected motion.
Timestamps are calculated as `frame_number / source_fps`.

Override the target sampling rate before starting Django and the worker if needed:

```powershell
$env:VIDEO_SAMPLING_TARGET_FPS = "5"
$env:VIDEO_MOTION_CHECK_FPS = "2"
$env:VIDEO_MOTION_THRESHOLD = "2"
$env:VIDEO_ACTIVE_SAMPLING_FPS = "10"
$env:VIDEO_ACTIVE_WINDOW_SECONDS = "3"
$env:VIDEO_PRE_ROLL_SECONDS = "1"
```

Set `VIDEO_ADAPTIVE_SAMPLING_DEBUG=true` before starting the worker to log fixed samples and each
motion score while comparing the fixed and adaptive paths.

## Test adaptive sampling

Restart the Celery worker after changing these settings. Upload a mostly static MP4, then a
video with visible movement, using the same upload command above.

- A mostly static video should finish with `active_windows=0` (or a small number) and few or no
  `Active sampled` log lines.
- A moving video should log `Motion detected`, an active-window range, and `Active sampled`
  lines at about `VIDEO_ACTIVE_SAMPLING_FPS` until the window expires. Continued movement extends
  the active window.

For extra detail while tuning the threshold, start the worker with:

```powershell
$env:VIDEO_ADAPTIVE_SAMPLING_DEBUG = "true"
celery -A VisionQuery worker --loglevel=INFO --pool=solo
```

## Notes for the demo / viva

- Keep the demo clip short (10–30s) — CLIP embedding runs on CPU by default, so a 30s clip at
  the default sampling rates typically embeds in well under a minute on a modern laptop.
- Pre-warm the CLIP model before presenting (upload one throwaway clip beforehand) — the first
  call in a fresh worker process both downloads weights (first run ever) and loads the model into
  memory (every process start), which adds noticeable delay to the *first* video only.
- Good example queries to show semantic (not just keyword) matching: describe an action
  ("someone waves"), an object ("a red car"), or a scene ("an empty room") rather than exact
  on-screen text.
- The admin gallery (`/admin/`) is a fast way to show the grader that fixed vs. active sampling
  is actually producing a different frame density during motion.

## Stop services

```powershell
docker compose down
```

Use `docker compose down -v` only if you also want to remove the local PostgreSQL data volume.
