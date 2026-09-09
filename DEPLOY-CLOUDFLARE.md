# Deploying RehnumaRent — Cloudflare Workers (frontend) + Render (backend)

Cloudflare Workers cannot run the FastAPI backend: it needs a real Linux process for asyncpg,
Redis and WeasyPrint's Pango/Cairo stack. (Cloudflare Containers *can* run the Docker image, but
that requires the Workers Paid plan — see "Going all-Cloudflare" at the bottom.)

So this split, both on free tiers:

| Piece | Where | Cost |
|---|---|---|
| Next.js frontend | Cloudflare Workers (`@opennextjs/cloudflare`) | free |
| FastAPI backend | Render, Docker web service | free |
| Postgres + Redis | Render managed, free plans | free |
| Object storage | local filesystem by default; Cloudflare R2 optional | free |

The browser only ever talks to the Worker. `/api/*` is proxied to Render **server-side** by
[web/app/api/[...path]/route.ts](web/app/api/%5B...path%5D/route.ts), so the app stays
same-origin, there is no CORS, and no API key can reach the client.

---

## 1. Backend on Render (do this first — you need its URL for step 2)

1. Sign up at https://render.com (no credit card needed for free plans).
2. **New + → Blueprint** → connect this repo → **Apply**. [render.yaml](render.yaml) creates
   `rehnumarent-api` (Docker), `rehnumarent-db` (Postgres 16) and `rehnumarent-redis`, all on free plans.
3. Optionally set `GROQ_API_KEY` on the `rehnumarent-api` service. Without it Rehnuma still replies,
   but with its safe canned advisory instead of live LLM answers.
4. First boot runs Alembic migrations and seeds the Bahria plot grid (`AUTO_SEED=true`).
   Confirm: `curl https://rehnumarent-api-XXXX.onrender.com/health` → `{"status":"ok",...,"plots_seeded":1920}`.
5. Add demo listings — service → **Shell**:
   ```bash
   python -m app.seed_demo
   python -m app.seed_scraped
   ```

Copy the service's hostname (e.g. `rehnumarent-api-XXXX.onrender.com`).

## 2. Frontend on Cloudflare Workers

From the `web/` directory:

```bash
cd web
npm install
npx wrangler login            # opens a browser; authorizes this machine
```

Point the Worker at your Render backend — edit `API_PROXY_TARGET` in
[web/wrangler.jsonc](web/wrangler.jsonc) to the hostname from step 1 (a bare hostname is fine,
the proxy prepends `https://`):

```jsonc
"vars": { "API_PROXY_TARGET": "rehnumarent-api-XXXX.onrender.com" }
```

Then deploy:

```bash
npm run deploy
```

Wrangler prints the live URL: `https://rehnumarent.<your-subdomain>.workers.dev`. That is the
URL you share.

To try it in the real Workers runtime before deploying: `npm run preview` (serves on :8788).

## 3. Verify

```bash
curl https://rehnumarent.<subdomain>.workers.dev/api/health     # via the Worker's proxy
```
Expect the backend's JSON health payload. The **first** request after 15 minutes idle takes
30-60s while Render's free instance cold-starts — that is the free tier, not a bug.

Then click the tenant flow: search LIVE listings → detail → ask Rehnuma → verify (OTP) → chat →
offer + "Fair?" → agreement PDF.

---

## Free-tier caveats

- **Cold starts.** Render free web services sleep after 15 min idle. A `starter` plan ($7/mo)
  removes this.
- **Postgres expires after 90 days** on Render's free plan. For something permanent, create a
  free Neon database (https://neon.tech), drop `rehnumarent-db` from the blueprint, and set
  `DATABASE_URL` to the Neon connection string — the app rewrites `postgres://` to the asyncpg
  driver itself ([app/config.py](app/config.py#L15-L22)).
- **Uploads are ephemeral.** Free Render services have no persistent disk, and with no object
  storage configured the app writes to `STORAGE_DIR` in the container
  ([app/storage.py](app/storage.py)). Agreement PDFs regenerate from the deal's locked terms, so
  they survive; uploaded listing photos do not. Fix with R2 below.
- **OTP delivery.** Without `WHATSAPP_TOKEN` codes cannot be sent, and with `ENV=prod` the dev
  code is not returned in the response either. To demo the verification flow, set `ENV=dev` on
  the API service so the OTP is echoed back.

## Optional: durable uploads with Cloudflare R2

R2's free tier is 10 GB with no egress charge, and it is S3-compatible, so the existing MinIO
client works unchanged.

1. Cloudflare dashboard → **R2** → create a bucket named `rehnumarent`.
2. **Manage R2 API Tokens** → create a token with Object Read & Write → note the Access Key ID,
   Secret Access Key and your account ID.
3. On the Render `rehnumarent-api` service, add:
   - `MINIO_ENDPOINT` = `<account-id>.r2.cloudflarestorage.com`
   - `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` = the token values
   - `MINIO_BUCKET` = `rehnumarent` · `MINIO_SECURE` = `true`

Setting `MINIO_ACCESS_KEY` is what flips the app from the filesystem backend to S3.

## Going all-Cloudflare

With the **Workers Paid** plan ($5/mo) the backend can move to
[Cloudflare Containers](https://developers.cloudflare.com/containers/) using the existing
[Dockerfile](Dockerfile), removing Render. Postgres and Redis would still be external (Cloudflare
has no managed Postgres — Hyperdrive only pools connections to someone else's). Expect roughly
$5-12/mo depending on how much the container is awake.
