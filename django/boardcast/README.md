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
