#!/usr/bin/env sh
set -e

CONFIG_FILE="/janus/janus.jcfg"

if [ -n "${JANUS_PUBLIC_IP:-}" ]; then
  sed -i "s/__JANUS_PUBLIC_IP__/${JANUS_PUBLIC_IP}/g" "$CONFIG_FILE"
else
  sed -i '/nat_1_1_mapping/d' "$CONFIG_FILE"
fi

JANUS_BIN="$(command -v janus || true)"
if [ -z "$JANUS_BIN" ]; then
  if [ -x /opt/janus/bin/janus ]; then
    JANUS_BIN="/opt/janus/bin/janus"
  elif [ -x /usr/local/bin/janus ]; then
    JANUS_BIN="/usr/local/bin/janus"
  else
    echo "janus binary not found"
    exit 1
  fi
fi

exec "$JANUS_BIN" -c "$CONFIG_FILE"
