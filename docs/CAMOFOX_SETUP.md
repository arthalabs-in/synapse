# Camofox Setup

Camofox is optional. SYNAPSE treats it as an external browser REST server used only when a public page is JavaScript-heavy and the basic HTTP fetcher returns no useful text.

Expected local base URL:

```bash
http://localhost:9377
```

Health check:

```bash
curl http://localhost:9377/health
```

Configuration:

```env
CAMOFOX_ENABLED=false
CAMOFOX_BASE_URL=http://localhost:9377
CAMOFOX_HEALTH_PATH=/health
CAMOFOX_FETCH_PATH=
CAMOFOX_TIMEOUT_SECONDS=30
CAMOFOX_SCREENSHOT=false
```

`CAMOFOX_FETCH_PATH` is intentionally blank by default because Camofox deployments may expose different fetch or snapshot endpoints. Set it to the REST path that accepts a JSON body like `{"url": "https://public.example"}` and returns readable `text`, `content`, or `markdown`.

Do not use Camofox to bypass logins, private pages, paywalls, CAPTCHA, or other access controls. If the HTTP fetcher and Camofox both fail, SYNAPSE records a failed source fetch and continues in degraded mode.
