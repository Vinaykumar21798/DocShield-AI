# Run Profiles

DocShield-AI provides separate local Python and Docker Compose profiles. Keep their ports and configuration sources separate.

## Local Python

Local endpoints:

- UI/API: `http://localhost:8000/ui/`
- PostgreSQL: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- Ollama, when used: `http://localhost:11434`

Initialize:

```powershell
cd <path-to-repo>
.\scripts\local-init.ps1
```

Initialization creates `.venv`, copies `.env.example` to `.env.local` when needed, installs dependencies, and installs a spaCy English model. Local scripts invoke the virtual-environment interpreter explicitly and set `DOCSHIELD_ENV_FILE=.env.local`.

Edit `.env.local` and replace all placeholders, especially `DATABASE_URL`. Do not commit `.env.local`.

For Ollama:

```ini
LLM_PROVIDER=gemma
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
BYPASS_LLM=false
```

For Azure OpenAI:

```ini
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=replace_me
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
BYPASS_LLM=false
```

The LLM residual path uses bounded candidate contexts and a maximum of three prioritized contexts. `BYPASS_LLM=true` disables both residual discovery and LLM validation.

Check dependencies and service connectivity:

```powershell
.\scripts\local-check.ps1
```

Apply migrations:

```powershell
.\scripts\local-migrate.ps1
```

Start the API and worker in separate terminals:

```powershell
.\scripts\local-api.ps1
.\scripts\local-worker.ps1
```

## Docker

Docker Compose uses environment values defined in `docker-compose.yml`, not `.env.local`.

Host endpoints:

- UI/API: `http://localhost:8001/ui/`
- PostgreSQL: `127.0.0.1:5433`
- Redis: `127.0.0.1:6380`
- Ollama from containers: `http://host.docker.internal:11434`

Start, inspect logs, and stop:

```powershell
.\scripts\docker-up.ps1
.\scripts\docker-logs.ps1
.\scripts\docker-down.ps1
```

The Compose credentials and port mappings are development defaults. Review and replace them before any shared or non-local deployment.

## Configuration precedence

Process environment variables take precedence. When the default environment-file profile is used, `.env.local` is loaded before `.env`. When `DOCSHIELD_ENV_FILE` names a custom file, `.env.local` is not loaded automatically.

## Rules

- Never commit `.env`, `.env.local`, credentials, tokens, or connection strings.
- Keep local PostgreSQL on `5432`; Docker publishes PostgreSQL on `5433`.
- Keep local Redis on `6379`; Docker publishes Redis on `6380`.
- Do not add fixed `container_name` values to Compose.
- Keep runtime files under `storage/` ignored except `.gitkeep` placeholders.
- Run API and worker with the same intended database, Redis, and LLM settings.
