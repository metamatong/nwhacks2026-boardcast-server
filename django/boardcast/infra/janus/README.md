## Janus on Fly

This folder contains a Fly deployable Janus setup for the Videoroom plugin.

### Deploy
```bash
cd django/boardcast
fly launch --no-deploy --config infra/janus/fly.toml
fly ips allocate-v4
fly deploy --config infra/janus/fly.toml
```

This build compiles Janus from source to avoid Docker registry auth issues.

### Set public IP (recommended)
If you allocated a dedicated IPv4, set it so Janus advertises the correct host
in ICE candidates:
```bash
fly secrets set JANUS_PUBLIC_IP=<your_fly_ipv4> --config infra/janus/fly.toml
```

### Django settings
Set these in `django/boardcast/.env` (and Fly secrets for your Django app):
```
JANUS_URL=https://<janus-app>.fly.dev/janus
JANUS_PUBLIC_URL=https://<janus-app>.fly.dev/janus
```
