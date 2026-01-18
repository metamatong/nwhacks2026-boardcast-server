# AGENTS

This repository is a server-only Django project. The active Django root is
`django/boardcast` (not the repo root). Client-side code is intentionally
ignored.

## Project Overview
- Stack: Django + DRF + Channels + Celery.
- Redis is required for Channels + Celery (Upstash supported).
- Database uses `DATABASE_URL` (Neon/Postgres recommended).
- Media uploads are stored locally under `uploaded_media/`.
- Janus SFU is used for video/audio broadcast (Django relays metadata only).

## Key Paths
- `django/boardcast/config/`: Django settings, ASGI/WSGI, routing, Celery app.
- `django/boardcast/rooms/`: Room create/join + ICE config.
- `django/boardcast/rooms/janus.py`: Janus Videoroom creation helper.
- `django/boardcast/realtime/`: WebSocket relay consumer + health endpoint.
- `django/boardcast/media_ingest/`: Audio chunk upload.
- `django/boardcast/intelligence/`: Celery task stubs (transcript/highlight).
- `django/boardcast/infra/`: Redis docker compose + TURN config placeholder.

## API Endpoints
- `POST /api/rooms/create/`: create a room, returns `id` and `join_code`.
- `POST /api/rooms/join/`: join by `room_id` (and `join_code` if set).
- `GET /api/rooms/ice-config/`: returns ICE servers using TURN settings.
- `POST /api/media/audio-chunks/`: upload audio chunk, triggers worker task.
- `GET /api/realtime/health/`: simple health check.

## WebSocket
- Path: `/ws/rooms/<room_id>/`
- Group: `room_<room_id>`
- Consumer relays any JSON payload to the group; ignores sender echo.
- Worker pushes:
  - `{ "type": "transcript", "text": "..." }`
  - `{ "type": "highlight", "title": "...", "detail": "..." }`

## Env Config (in `django/boardcast/.env`)
- `DATABASE_URL`: Neon/Postgres connection string (include `sslmode=require`).
- `REDIS_URL`: Upstash must be `rediss://.../0?ssl_cert_reqs=required`.
- `TURN_*`: used for ICE config and `infra/turnserver.conf`.
- `JANUS_URL`: base Janus HTTP endpoint (e.g. `http://localhost:8088/janus`).
- `JANUS_API_SECRET`/`JANUS_ADMIN_KEY`: optional Janus auth values.
- `CORS_ALLOWED_ORIGINS`: comma-separated list.

## Run Commands
- Server: `cd django/boardcast && python manage.py runserver 0.0.0.0:8000`
- Worker: `cd django/boardcast && celery -A config worker -l info`

## Notes
- `django/boardcast/api` and `django/boardcast/users` exist but are not used.
- ASGI (Channels) is configured in `django/boardcast/config/asgi.py`.
