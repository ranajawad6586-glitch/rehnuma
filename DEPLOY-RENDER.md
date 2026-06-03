# Deploying RehnumaRent to Render

This is a paid, multi-service deploy (Postgres + Redis + two web services + object storage).
The repo is already Render-ready ([render.yaml](render.yaml), `$PORT`-aware Dockerfiles, a
runtime API proxy). You do the account/repo/secret steps below.

## 0. Prerequisites
- A **GitHub** (or GitLab) repo with this code (the project isn't a git repo yet — see step 1).
- A **Render** account (https://render.com) with billing enabled.
- An **S3-compatible bucket** for PDFs/photos. Cloudflare **R2** is easiest (free tier):
  create a bucket + an API token (Access Key ID / Secret) at https://dash.cloudflare.com → R2.

## 1. Push the code to GitHub
```bash
cd /Users/jawad123/Development/real-estate
git init && git add -A && git commit -m "RehnumaRent MVP"
git branch -M main
git remote add origin https://github.com/<you>/rehnuma-rent.git
git push -u origin main
```
`.env` is gitignored and dockerignored — your secrets won't be committed. **Rotate your Apify
token** before pushing if it was ever shown anywhere; never commit it.

## 2. Create the Blueprint on Render
Render dashboard → **New + → Blueprint** → connect the repo. Render reads `render.yaml` and
proposes: `rehnuma-db` (Postgres), `rehnuma-redis`, `rehnuma-api`, `rehnuma-web`. Click **Apply**.

## 3. Set the dashboard-only env vars (on `rehnuma-api`)
These are marked `sync: false` so they're not in git — set them in the service's Environment tab:
- `MINIO_ENDPOINT` — e.g. `<account-id>.r2.cloudflarestorage.com`
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` — your R2 token
- (optional) `GROQ_API_KEY` — real Rehnuma answers
- (optional) `APIFY_TOKEN`, `APIFY_ACTOR_ID`, `APIFY_RUN_INPUT_JSON` — listing import

`MINIO_BUCKET` (default `rehnuma`) and `MINIO_SECURE=true` are already set. Create that bucket
in R2 first.

## 4. PostGIS
The first migration runs `CREATE EXTENSION IF NOT EXISTS postgis` on boot. Render's paid
Postgres supports PostGIS; if the API logs show an extension/permission error, enable PostGIS
from the database's dashboard (or psql as the owner) once, then redeploy the API.

## 5. Deploy & seed
On first boot the API runs Alembic migrations and (`AUTO_SEED=true`) seeds the Bahria grid.
To add demo/scraped listings, open the `rehnuma-api` **Shell** in Render and run:
```bash
python -m app.seed_demo
python -m app.seed_scraped
python -m app.jobs.apify_import      # if Apify env vars are set
```

## 6. Open it
Visit the `rehnuma-web` URL (`https://rehnuma-web.onrender.com`). It proxies `/api/*` to the API
server-side, so no key is exposed and there's no CORS to configure.

---

## Notes, costs & caveats
- **Not free.** Postgres (PostGIS needs a paid plan), Redis, and two web services on Starter add
  up; check Render's pricing. The blueprint uses `basic-256mb`/`starter`/`free` as starting points.
- **Object storage is external** (R2/S3). The local docker-compose still bundles MinIO; on Render
  we point the same S3 client at R2 via the `MINIO_*` vars.
- **Migrations run on API boot.** Keep the API at a single instance (or run migrations as a
  one-off) to avoid concurrent `alembic upgrade head` on deploys.
- **WhatsApp OTP**: without `WHATSAPP_TOKEN`, OTP delivery falls back to the console sender, and
  in **prod** (`ENV=prod`) the dev code is **not** returned in the response — so set up WhatsApp
  Business API before real users, or you can't receive codes.
- **Cold starts**: free/low tiers spin down when idle; the first request after idle is slow.
- Schedule `python -m app.jobs.comp_refresh` / `verification_batch` / `apify_import` as Render
  **Cron Jobs** if you want the periodic refresh.
