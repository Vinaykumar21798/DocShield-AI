# Run Profiles

DocShield-AI has two separate runtime profiles.

## Local Python

Local Python uses private `.env.local` generated from `.env.example` and local service ports:

- API: `http://localhost:8000/ui/`
- PostgreSQL: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- Ollama: `http://localhost:11434`

Setup:

```powershell
cd E:\Office\DocShield-AI
.\scripts\local-init.ps1
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Edit `.env.local` and set the real PostgreSQL password in both `POSTGRES_PASSWORD` and `DATABASE_URL`.

Check dependencies:

```powershell
.\scripts\local-check.ps1
```

Run migrations:

```powershell
.\scripts\local-migrate.ps1
```

Run API:

```powershell
.\scripts\local-api.ps1
```

Run worker in a second terminal:

```powershell
.\scripts\local-worker.ps1
```

## Docker

Docker Compose does not use `.env.local` or `.env.example`. Container environment values are pinned in `docker-compose.yml` so local host credentials do not leak into Docker.

Docker host ports:

- API: `http://localhost:8001/ui/`
- PostgreSQL: `127.0.0.1:5433`
- Redis: `127.0.0.1:6380`
- Ollama from containers: `http://host.docker.internal:11434`

Start Docker:

```powershell
.\scripts\docker-up.ps1
```

Watch API and worker logs:

```powershell
.\scripts\docker-logs.ps1
```

Stop Docker:

```powershell
.\scripts\docker-down.ps1
```

## Rules

- Do not use `.env` for normal development. Use `.env.local` for local Python.
- Do not expose Docker Postgres on `5432`; Docker uses `5433` on the host.
- Do not expose Docker Redis on `6379`; Docker uses `6380` on the host.
- Do not add fixed `container_name` values back into Compose; they cause stale-container conflicts.
- Keep runtime files under `storage/` ignored except `.gitkeep` placeholders.
