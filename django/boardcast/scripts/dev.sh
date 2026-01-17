#!/usr/bin/env bash
set -euo pipefail

# 1) start redis
docker compose -f infra/docker-compose.yml up -d

# 2) run migrations
python manage.py makemigrations
python manage.py migrate

# 3) run server
python manage.py runserver 0.0.0.0:8000
