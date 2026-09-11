# VisionQuery

Minimal proof-of-flow backend for uploading a video, dispatching background work, and polling the job status.

## What is included

- Django + Django REST Framework API in `backend/`
- PostgreSQL with the `pgvector` extension enabled
- Celery with Redis as both its broker and result backend
- `VideoUpload` records with `pending`, `processing`, `done`, and `failed` status options

The Celery task uses OpenCV to inspect the uploaded video. It retains fixed 5 FPS sampling for comparison and adds lightweight motion-triggered sampling: frames are checked for change at 2 FPS and sampled at 10 FPS only during short active windows. It does not run ML processing or persist sampled frames.

## Prerequisites

- Python 3.11+ recommended
- Docker Desktop (for PostgreSQL + Redis), or local PostgreSQL with the `vector` extension installed and Redis

## Start PostgreSQL and Redis

From the repository root:

```powershell
docker compose up -d
docker compose ps
```

This starts PostgreSQL on `localhost:5432` and Redis on `localhost:6379`. PostgreSQL uses database/user/password `visionquery`.

The database container enables `vector` on first initialization. The Django migration also uses `CREATE EXTENSION IF NOT EXISTS vector`, so the extension is enabled when migrations run against a local pgvector-enabled PostgreSQL instance.

## Install the Django backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
```

When using the repository's Docker Compose services, make sure the Django process uses the same database credentials as Compose. Environment variables override any values in `backend/.env`:

```powershell
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "visionquery"
$env:POSTGRES_USER = "visionquery"
$env:POSTGRES_PASSWORD = "visionquery"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
```

## Run Django and Celery

Use two terminals, each with the virtual environment activated and working directory set to `backend`.

Terminal 1:

```powershell
python manage.py runserver
```

Terminal 2:

```powershell
celery -A VisionQuery worker --loglevel=INFO --pool=solo
```

## Try the flow

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

Initially the response has `"status":"pending"`, then becomes `"processing"` while the worker reads the file. When it finishes, it becomes:

```json
{"video_id":1,"status":"done","uploaded_at":"..."}
```

The Celery worker logs source FPS, frame count, duration, motion windows, and active samples. For a 30 FPS source video, fixed sampling selects frames 0, 6, 12, and so on; active sampling selects roughly 10 frames per second only around detected motion. Timestamps are calculated as `frame_number / source_fps`.

Override the target sampling rate before starting Django and the worker if needed:

```powershell
$env:VIDEO_SAMPLING_TARGET_FPS = "5"
$env:VIDEO_MOTION_CHECK_FPS = "2"
$env:VIDEO_MOTION_THRESHOLD = "2"
$env:VIDEO_ACTIVE_SAMPLING_FPS = "10"
$env:VIDEO_ACTIVE_WINDOW_SECONDS = "3"
$env:VIDEO_PRE_ROLL_SECONDS = "1"
```

Set `VIDEO_ADAPTIVE_SAMPLING_DEBUG=true` before starting the worker to log fixed samples and each motion score while comparing the fixed and adaptive paths.

## Test adaptive sampling

Restart the Celery worker after changing these settings. Upload a mostly static MP4, then a video with visible movement, using the same upload command above.

- A mostly static video should finish with `active_windows=0` (or a small number) and few or no `Active sampled` log lines.
- A moving video should log `Motion detected`, an active-window range, and `Active sampled` lines at about `VIDEO_ACTIVE_SAMPLING_FPS` until the window expires. Continued movement extends the active window.

For extra detail while tuning the threshold, start the worker with:

```powershell
$env:VIDEO_ADAPTIVE_SAMPLING_DEBUG = "true"
celery -A VisionQuery worker --loglevel=INFO --pool=solo
```

## Stop services

```powershell
docker compose down
```

Use `docker compose down -v` only if you also want to remove the local PostgreSQL data volume.
