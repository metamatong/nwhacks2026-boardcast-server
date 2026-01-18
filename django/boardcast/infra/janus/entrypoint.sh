#!/usr/bin/env sh
set -e

CONFIG_FILE="/janus/janus.jcfg"
ALT_CONFIG_FILE="/opt/janus/etc/janus/janus.jcfg"
CERT_DIR="/janus/certs"
CERT_FILE="${CERT_DIR}/janus.crt"
KEY_FILE="${CERT_DIR}/janus.key"

for CFG in "$CONFIG_FILE" "$ALT_CONFIG_FILE"; do
  if [ -f "$CFG" ]; then
    if [ -n "${JANUS_PUBLIC_IP:-}" ]; then
      sed -i "s/__JANUS_PUBLIC_IP__/${JANUS_PUBLIC_IP}/g" "$CFG"
    else
      sed -i '/nat_1_1_mapping/d' "$CFG"
    fi
  fi
done

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  mkdir -p "$CERT_DIR"
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 3650 \
    -subj "/CN=janus"
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

exec "$JANUS_BIN" -C "$CONFIG_FILE" -c "$CERT_FILE" -k "$KEY_FILE"
