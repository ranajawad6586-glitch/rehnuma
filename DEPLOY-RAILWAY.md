# Deploying RehnumaRent to Railway

The app no longer needs PostGIS, so Railway's one-click **Postgres** and **Redis** plugins work
directly. The Dockerfiles honor `$PORT`, the DB URL auto-converts to the asyncpg driver, and the
web app proxies `/api/*` to the backend at runtime — so there's little to configure.

Repo: https://github.com/ranajawad6586-glitch/rehnuma

## 1. New project + databases
1. Railway → **New Project → Deploy from GitHub repo** → pick the repo.
2. In the project, **+ New → Database → Add PostgreSQL**.
3. **+ New → Database → Add Redis**.

## 2. API service (FastAPI)
The first deployed service is the API (Railway auto-detects the root `Dockerfile`). In its
**Settings**: Root Directory = `/` (repo root). In **Variables** add:
- `ENV` = `prod`
- `AUTO_SEED` = `true`
- `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`   ← reference the Postgres plugin
- `REDIS_URL` = `${{Redis.REDIS_URL}}`            ← reference the Redis plugin
- `SECRET_KEY`, `HASH_PEPPER`, `PHONE_ENCRYPTION_SECRET` = (any long random strings)
- Object storage (Cloudflare R2 — free; create a bucket + API token):
  - `MINIO_ENDPOINT` = `<account-id>.r2.cloudflarestorage.com`
  - `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` = your R2 keys
  - `MINIO_BUCKET` = `rehnuma`  · `MINIO_SECURE` = `true`
- Optional: `GROQ_API_KEY`, `APIFY_TOKEN`, `APIFY_ACTOR_ID`, `APIFY_RUN_INPUT_JSON`

Generate a public domain for it: **Settings → Networking → Generate Domain**.

## 3. Web service (Next.js)
**+ New → GitHub Repo** (same repo) → in its **Settings** set **Root Directory = `web`**
(Railway then uses `web/Dockerfile`). In **Variables**:
- `API_PROXY_TARGET` = `${{<api-service-name>.RAILWAY_PUBLIC_DOMAIN}}`
  (the proxy prepends `https://` automatically). Or use the API's private address
  `http://${{<api-service-name>.RAILWAY_PRIVATE_DOMAIN}}:${{<api-service-name>.PORT}}`.

Generate a public domain for the web service — that's the URL you visit.

## 4. First boot
The API runs Alembic migrations and seeds the Bahria grid (`AUTO_SEED=true`). To add demo
listings, open the API service's shell (Railway → service → **Shell**) and run:
```bash
python -m app.seed_demo
python -m app.seed_scraped
python -m app.jobs.apify_import     # if Apify vars are set
```

## Notes
- **Cost:** Railway's free trial gives a usage credit; beyond it, Postgres/Redis/services are
  usage-billed. No PostGIS plan needed anymore.
- **WhatsApp OTP:** without `WHATSAPP_TOKEN`, codes aren't deliverable and in `ENV=prod` the dev
  code isn't returned — set up WhatsApp Business API before real users.
- **Object storage** is external (R2/S3); local dev still bundles MinIO via docker-compose.
- Schedule `app.jobs.comp_refresh` / `apify_import` as Railway **Cron** services if wanted.
