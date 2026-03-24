# StockFlow Backend (FastAPI + MongoDB)

This service powers the StockFlow SaaS backend using **FastAPI** and **MongoDB** (Beanie ODM).

## Requirements

- Python 3.10+ (Windows/macOS/Linux)
- A MongoDB instance (local MongoDB or MongoDB Atlas)

## Environment variables

The backend reads config from `.env` (and also supports `backend.env`).

Create/update `stock-management-server/.env` with at least:

- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `SECRET_KEY`
- `BACKEND_CORS_ORIGINS` (for local frontend)

Email is optional, but if you want email notifications:

- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM`
- `MAIL_SERVER`
- `MAIL_PORT`

**Important**: keep `.env` private (it contains secrets).

## Install dependencies

From the `stock-management-server` folder:

```bash
python -m pip install -r requirements.txt
```

If you use `run_server.sh`, it will also install these requirements automatically.

## Run the server (recommended)

### Option A: Run directly (works on Windows too)

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API root: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`

### Option B: Use the included `run_server.sh` (Linux/macOS/Git Bash)

This script creates a `.venv`, installs requirements, and starts Uvicorn:

```bash
./run_server.sh
```

Notes:
- `run_server.sh` uses `source .venv/bin/activate`, so it’s designed for Linux/macOS shells.
- On Windows, prefer “Option A” above or create/activate a venv manually (see below).

## Virtual environment (optional but recommended)

### Git Bash (Windows)

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

If PowerShell blocks activation, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Core usage (how the API works)

- Multi-tenant: most entities are scoped by `organization_id`.
- Auth: OAuth2 password flow at `POST /api/v1/auth/login/access-token`.
- Paywall/approval: business-staff requests are gated by org approval + trial/subscription status.

## Admin/Billing helpers

### Backfill billing fields (safe)

This repo includes a script to backfill billing/subscription fields and ensure plans have XAF currency:

Dry-run (no writes):

```bash
python scripts/backfill_billing_fields.py
```

Apply changes:

```bash
python scripts/backfill_billing_fields.py --apply
```

### Key endpoints (platform admin)

- Approve organization: `POST /api/v1/organizations/{id}/approve`
- Extend trial: `POST /api/v1/organizations/{id}/extend-trial?days=30`
- Set storage quota: `PUT /api/v1/organizations/{id}/storage-capacity?storage_capacity_kb=...`
- Storage overview: `GET /api/v1/organizations/all/storage/overview`

## Troubleshooting

- **Mongo connection errors**: confirm `MONGODB_URL` and network access (Atlas IP allowlist).
- **Email not sending**: backend will still work; alerts still appear in dashboard. Check SMTP vars.
- **CORS errors**: set `BACKEND_CORS_ORIGINS` to include your frontend URL(s).

