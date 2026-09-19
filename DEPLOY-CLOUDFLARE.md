# Deploying RehnumaRent — Cloudflare Workers (frontend) + Render (backend)

Cloudflare Workers cannot run the FastAPI backend: it needs a real Linux process for asyncpg,
Redis and WeasyPrint's Pango/Cairo stack. (Cloudflare Containers *can* run the Docker image, but
that requires the Workers Paid plan — see "Going all-Cloudflare" at the bottom.)

So this split, both on free tiers:

| Piece | Where | Cost |
|---|---|---|
| Next.js frontend | Cloudflare Workers (`@opennextjs/cloudflare`) | free |
| FastAPI backend | Render, Docker web service | free |
| Postgres | Neon | free |
| Redis | Upstash | free |
| Object storage | local filesystem by default; Cloudflare R2 optional | free |

The browser only ever talks to the Worker. `/api/*` is proxied to Render **server-side** by
[web/app/api/[...path]/route.ts](web/app/api/%5B...path%5D/route.ts), so the app stays
same-origin, there is no CORS, and no API key can reach the client.

---

## 1. Backend (do this first — you need its URL for step 2)

Three free accounts, none of which asks for a card. Render's *managed database* is what forces
a paid plan (a free account gets only one, and yours may already be used), so the database and
Redis come from elsewhere.

### 1a. Postgres — Neon
1. https://neon.tech → sign in with GitHub → create a project (any name, any region).
2. Copy **your own** connection string from the Connect panel — its shape is
   `postgresql://<user>:<password>@<your-endpoint>.<region>.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.
   Keep the query parameters; the app rewrites them for asyncpg ([app/dburl.py](app/dburl.py)).
3. Prefer the **direct** endpoint over the pooled one (the host *without* `-pooler`). The pooled
   endpoint is PgBouncer in transaction mode, which collides with asyncpg's prepared-statement
   cache; the app disables that cache automatically when it sees a `-pooler` host, but the
   direct endpoint is the better fit for a single long-lived container.

### 1b. Redis — Upstash
1. https://upstash.com → sign in with GitHub → **Create Database** (Redis, any region).
2. Copy the **`rediss://`** connection URL — not the REST URL, and not the `redis-cli --tls -u
   ...` example command. The value must begin with `rediss://` (two s's, for TLS).

### 1c. FastAPI — Render
1. **https://render.com/deploy?repo=https://github.com/ranajawad6586-glitch/rehnuma**
   If it says your email already exists, you have an account — sign in at
   https://dashboard.render.com/login with **GitHub/Google** rather than creating a new one.
2. Render reads [render.yaml](render.yaml) and prompts for the two values above:
   `DATABASE_URL` (Neon) and `REDIS_URL` (Upstash). Optionally add `GROQ_API_KEY`. → **Apply**.
3. First boot runs Alembic migrations and seeds the Bahria plot grid (`AUTO_SEED=true`).
   Confirm: `curl https://rehnumarent-api-XXXX.onrender.com/health` →
   `{"status":"ok",...,"plots_seeded":1920}`.
4. Add demo listings — service → **Shell**:
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
```

Authenticate with an **API token** rather than `wrangler login` — the token works headlessly and
does not expire, whereas deploying without credentials lands on a throwaway preview account
whose URL Cloudflare reclaims within hours:

1. https://dash.cloudflare.com/profile/api-tokens → **Create Token**
2. Use the **"Edit Cloudflare Workers"** template, defaults unchanged → **Create Token**
3. Save it somewhere only you can read, e.g. `~/.cloudflare-token` (chmod 600)

Point the Worker at your Render backend — edit `API_PROXY_TARGET` in
[web/wrangler.jsonc](web/wrangler.jsonc) to the hostname from step 1 (a bare hostname is fine,
the proxy prepends `https://`):

```jsonc
"vars": { "API_PROXY_TARGET": "rehnumarent-api-XXXX.onrender.com" }
```

Then deploy:

```bash
CLOUDFLARE_API_TOKEN=$(cat ~/.cloudflare-token) npx wrangler deploy
```

Wrangler prints the live URL: `https://rehnumarent.<your-subdomain>.workers.dev`. That is the
URL you share, and it stays the same on every redeploy.

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
- **Neon scales to zero** on the free plan, so the first query after an idle period takes an
  extra moment. It does not expire, unlike Render's free database.
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
