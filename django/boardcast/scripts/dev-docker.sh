#!/usr/bin/env bash
set -euo pipefail

profile="${1:-all}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
compose_file="${project_root}/infra/docker-compose.app.yml"

case "$profile" in
  app)
    profiles=(--profile app)
    ;;
  worker)
    profiles=(--profile worker)
    ;;
  all)
    profiles=(--profile app --profile worker)
    ;;
  *)
    echo "Usage: $0 [app|worker|all]" >&2
    exit 1
    ;;
esac

docker compose -f "${compose_file}" "${profiles[@]}" up --build
