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
