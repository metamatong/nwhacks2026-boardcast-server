# Whiteboard Server

Minimal Django + DRF + Channels skeleton for rooms, signaling relay, media ingest, and worker stubs.

## Quick start

```bash
cp .env.example .env
pip install -r requirements.txt
./scripts/dev.sh
```

## Run worker

```bash
celery -A config worker -l info
```

## Docker (optional)

Ensure `django/boardcast/.env` exists, then:

Start app only:

```bash
docker compose -f infra/docker-compose.app.yml --profile app up --build
```

Start worker only:

```bash
docker compose -f infra/docker-compose.app.yml --profile worker up --build
```

Start both app + worker:

```bash
docker compose -f infra/docker-compose.app.yml --profile app --profile worker up --build
```

Shortcut:

```bash
./scripts/dev-docker.sh all
```

Stop everything:

```bash
docker compose -f infra/docker-compose.app.yml down
```

## Fly.io (deploy)

From `django/boardcast/`:

1) Update `fly.toml` with your app name (or run `fly launch --no-deploy`).
2) Set secrets:

```bash
fly secrets set DJANGO_SECRET_KEY=... DJANGO_ALLOWED_HOSTS="your-app.fly.dev" REDIS_URL=... TURN_STATIC_AUTH_SECRET=...
```

3) Deploy:

```bash
fly deploy
```

Notes:
- Scale a worker machine after first deploy: `fly scale count web=1 worker=1`
- `DATABASE_URL` defaults to SQLite; for persistence use a Postgres URL.
- Set `CORS_ALLOWED_ORIGINS` if your client is on a different domain.
