# RehnumaRent

Direct-to-deal rental platform for **Bahria Town Islamabad** — no dealer in the loop.
Verified listings, a neutral AI realtor (Rehnuma), and a structured negotiation → agreement
pipeline. See [CLAUDE.md](CLAUDE.md) for the full spec and non-negotiable rules.

## Live

| | |
|---|---|
| App | https://rehnumarent.ranajawad6586.workers.dev |
| API | https://rehnumarent-api.onrender.com |

Frontend on Cloudflare Workers (the owner's own account, so the URL is permanent), backend on
Render's free tier, Postgres on Neon, Redis on Upstash. See [DEPLOY-CLOUDFLARE.md](DEPLOY-CLOUDFLARE.md).

Redeploy the frontend with:

```bash
cd web
CLOUDFLARE_API_TOKEN=$(cat ~/.cloudflare-token) npx wrangler deploy
```

Two caveats on the current deployment:

- Render's free tier sleeps after 15 minutes idle, so the first request wakes it in ~40s.
- `ENV=dev` is set so the OTP code comes back in the API response. Without it nobody can log
  in at all, since WhatsApp delivery is not configured — but it does mean anyone can verify
  any phone number. Fine for a demo, not for real users.

## Status

- **M1 — Skeleton** ✅ FastAPI + Postgres/PostGIS + Redis via Docker Compose, health check,
  seeded Bahria phase/sector/plot reference grid.
- **M2 — Auth + verification** ✅ Phone OTP (WhatsApp, with console dev fallback), CNIC capture,
  user records. Phone/CNIC stored only as keyed HMAC hashes — never raw, never returned to
  the client. Session via JWT bearer token.
- **M3 — Listings + plot match** ✅ Owner submits a listing; `{phase, sector, house_ref}` is
  matched against the seeded Bahria grid (no match → rejected); listing status machine; only
  `LIVE` listings exposed to tenants, and publishing to `LIVE` requires owner CNIC+OTP.
- **M4 — Rehnuma LLM router** ✅ [app/rehnuma_llm.py](app/rehnuma_llm.py) — `ask(messages,
  system, *, max_tokens=1000) -> str` with the fixed **Groq → Gemini → OpenRouter → Anthropic
  Haiku** fallback (plain httpx, no SDKs), per-call timeout, provider logging, and a safe canned
  advisory on total failure (never raises). Keys are server-side only; a provider with no key
  is skipped.
- **M5 — Rehnuma endpoint** ✅ `POST /ai/ask` proxies the router (keys never reach the client),
  carries conversation history, fills the system prompt from the listing + live comps when a
  `listing_id` is given, detects Roman Urdu vs English to match the reply, and persists each
  exchange to `ai_sessions` (with `provider_used`). The chat UI itself lands in M9.
- **M6 — Direct chat + privacy gate** ✅ Tenant↔owner deals + messaging. Chat opens only after
  the tenant clears CNIC + phone OTP (anti call-spam gate); neither party's phone is revealed
  until BOTH consent to share contact.
- **M7 — Structured offer engine** ✅ Discrete offers `{rent, advance_months, security,
  duration_months, move_in}`, the offer/counter loop, a deterministic "Fair?" verdict (vs
  asking rent + Bahria advance norms; 6-month advance = red flag), and terms-lock into
  `deals.locked_terms` on accept.
- **M8 — Agreement generator** ✅ Renders the locked terms into a stamp-paper-ready tenancy PDF
  (WeasyPrint), computes the stamp-duty band from **annual** rent (Rs 500 / 1,000 / 2,000 —
  never a fixed Rs 200), surfaces hedged e-stamping/registration advisories, generates the
  police verification form, and records offline signing.
- **M9 — Frontend** ✅ Next.js (App Router) + Tailwind "earthen" UI (moss/clay/paper, Fraunces +
  Outfit) at `:3000`, covering the full tenant flow: search LIVE listings → detail + ask Rehnuma
  → verify (OTP + CNIC) → inquiry/chat → offer builder with the "Fair?" check → contact gate →
  agreement PDF + police form. Browser stays same-origin; `/api/*` is proxied to FastAPI
  server-side so no key is ever exposed.
- **M10 — Hardening** ✅ Redis fixed-window rate limits (OTP per-IP, `/ai/ask` per-user) with
  `Retry-After`; request-id + structured access logging; a `/metrics` endpoint (Prometheus
  text); and OpenClaw-scheduled jobs for comp-data refresh and stale-listing expiry.

### Hardening (M10)

```
GET  /metrics                          Prometheus counters (requests by class, rate-limit hits)
python -m app.jobs.comp_refresh         cache market comps per (phase, size)   [daily cron]
python -m app.jobs.verification_batch   expire LIVE listings older than N days [daily cron]
```

Rate limits & the expiry window are configurable in [app/config.py](app/config.py). OpenClaw
(or any cron) runs the jobs on a schedule; both are idempotent and runnable standalone.

### Agreements (M8)

```
POST /deals/{id}/agreement                  (participant, deal ACCEPTED) -> generate PDF
GET  /deals/{id}/agreement                  metadata (duty band, advisories, terms)
GET  /deals/{id}/agreement/pdf              download the tenancy agreement PDF
GET  /deals/{id}/police-verification-form   download the police tenant-verification form PDF
POST /deals/{id}/sign                        AGREEMENT_GENERATED -> SIGNED_OFFLINE
```

This completes the deal lifecycle end-to-end:
`INQUIRY → CHAT_OPEN → OFFER_SENT ↔ COUNTERED → ACCEPTED → AGREEMENT_GENERATED → SIGNED_OFFLINE`.

### Offers (M7)

```
POST /deals/{id}/offers              (participant, chat open) send/counter an offer
GET  /deals/{id}/offers              (participant) offer history
POST /deals/{id}/offers/check        (participant) "Fair?" verdict for proposed numbers
POST /deals/{id}/offers/{oid}/accept (counter-party) -> deal ACCEPTED, terms locked
```

### Deals & chat (M6)

```
POST /deals/                      (tenant) inquiry on a LIVE listing (get-or-create) -> INQUIRY
POST /deals/{id}/open             (tenant, CNIC+OTP) -> CHAT_OPEN
POST /deals/{id}/messages         (participant, CHAT_OPEN) send a text message
GET  /deals/{id}/messages         (participant) chat history
POST /deals/{id}/share-contact    (participant) record consent; phone revealed once BOTH agree
GET  /deals/{id}                  (participant) deal + counter-party contact (only if shared)
GET  /deals/                      (me) deals where I'm tenant or listing owner
```

### Rehnuma AI (M5)

```
POST /ai/ask  {message, listing_id?, session_id?}  (Bearer) -> { session_id, reply, provider,
                                                                  language, fell_back }
GET  /ai/sessions/{id}                             (Bearer) -> transcript (owner-private)
```

Set a `GROQ_API_KEY` (free tier) to get real Rehnuma answers; with no keys the router returns
its neutral safe-advisory and `provider: "fallback"`.

### Listings (M3)

```
POST /listings                    (owner) submit -> grid match -> GRID_MATCHED
POST /listings/{id}/publish       (owner) -> LIVE  (requires CNIC+OTP verified)
POST /listings/{id}/delist        (owner) -> DELISTED
POST /listings/{id}/mark-rented   (owner) -> RENTED
GET  /listings/mine               (owner) all own listings, any status
GET  /listings                    (tenant) LIVE only; filters: phase, sector, size,
                                            min_rent, max_rent, beds, limit, offset
GET  /listings/{id}               (tenant) LIVE only (else 404)
```

Lifecycle: `DRAFT → PLOT_SUBMITTED → GRID_MATCHED → OWNER_VERIFIED → LIVE → (RENTED|EXPIRED|DELISTED)`.

### Auth flow (M2)

```
POST /auth/otp/request  {phone, name?, roles?}  -> sends OTP (dev echoes `dev_code`)
POST /auth/otp/verify   {phone, code}           -> { access_token, user }
POST /auth/cnic         {cnic}   (Bearer token) -> captures CNIC (hashed)
GET  /auth/me                    (Bearer token) -> current user
```

OTP codes are random, 5-min TTL, single-use, attempt-limited, with a resend cooldown.
With no `WHATSAPP_TOKEN`/`WHATSAPP_PHONE_ID` set, delivery falls back to a console sender and
the code is echoed in `dev_code` (dev only). Set those env vars to send real WhatsApp messages.

## Stack

FastAPI (Python 3.11) · SQLAlchemy 2.x async + asyncpg · PostgreSQL 16 + PostGIS · Redis ·
Docker Compose. No payments, no LLM keys client-side, dealer-free by design.

## Run (Docker)

```bash
docker compose up --build          # db (PostGIS), redis, the API, and the web app
# API auto-creates the schema on boot and (AUTO_SEED=true) seeds the Bahria grid if empty
docker compose run --rm api python -m app.seed_demo      # a few demo LIVE listings
docker compose run --rm api python -m app.seed_scraped  # ~40 real Rawalpindi rentals (Zameen)
```

- Web:    http://localhost:3000   (the tenant-facing app)
- API:    http://localhost:8000
- Docs:   http://localhost:8000/docs
- Health: http://localhost:8000/health

Seed manually (idempotent — skips if already seeded):

```bash
docker compose run --rm api python -m app.seed
```

Health check shows DB/PostGIS status and the seeded plot count:

```bash
curl -s localhost:8000/health
# {"status":"ok","app":"RehnumaRent","db":"up","postgis":"3.4...","plots_seeded":1920}
```

## Tests

```bash
# Inside the stack — runs everything, incl. DB-backed health + seed tests:
docker compose run --rm api python -m pytest -q

# Locally without Docker — the pure grid unit tests run; DB-backed tests skip:
python -m venv .venv && .venv/bin/pip install pytest pytest-asyncio
.venv/bin/python -m pytest -q
```

## The Bahria grid

`app/grid/bahria.py` deterministically generates the reference address space (phases 1–8,
sectors A–F, numbered houses → **1920 plots**). It is pure stdlib and fully unit-tested. The
real possession registry is not yet available, so coordinates/possession refs are structured
synthetic values clustered around Bahria Town ISB; the `{phase, sector, house_ref}` shape is
what listing verification (M3) matches against.

## Layout

```
app/
  main.py            FastAPI app + lifespan (schema bootstrap, optional auto-seed)
  config.py          settings (env / .env, server-side only)
  db.py              async engine/session, PostGIS + create_all bootstrap (boot retry)
  seed.py            idempotent Bahria grid seeder  (python -m app.seed)
  security.py        HMAC identifier hashing (peppered) + JWT session tokens
  redis_client.py    async Redis singleton
  api/health.py      /health — DB/PostGIS status + seeded count
  grid/bahria.py     deterministic Bahria reference grid (pure stdlib)
  models/plot.py     plots table (PostGIS POINT geom)
  models/user.py     users table (phone_hash, cnic_hash, role flags)
  models/listing.py  listings table (FKs to users/plots, status, photos JSONB)
  auth/validators.py PK phone -> E.164, CNIC validation (pure stdlib)
  auth/otp.py        Redis-backed OTP issue/verify (TTL, attempts, cooldown)
  auth/sender.py     OTP delivery: WhatsApp Business API + console dev fallback
  auth/router.py     /auth/* endpoints; deps.py = current-user dependency
  listings/status.py listing state machine + allowed transitions (pure stdlib)
  listings/router.py /listings endpoints (owner actions + tenant LIVE reads)
  rehnuma_llm.py     LLM router: fixed fallback chain, timeout, logging, safe-fail
  llm_providers.py   provider adapters (Groq/Gemini/OpenRouter/Anthropic, httpx)
  rehnuma_prompt.py  canonical neutral system prompt + context builder (pure stdlib)
  models/ai_session.py  ai_sessions table (transcript JSONB, provider_used)
  ai/language.py     Roman Urdu vs English detector (pure stdlib)
  ai/context.py      listing-aware context + comps from LIVE listings
  ai/router.py       /ai/ask proxy + /ai/sessions/{id} transcript
  models/deal.py     deals table (status, consent flags, locked_terms JSONB)
  models/message.py  messages table (deal_id, sender_id, body, type)
  deals/status.py    deal + offer state machines, message types (pure stdlib)
  deals/router.py    /deals endpoints: inquiry, open, messages, share-contact
  deals/fairness.py  "Fair?" evaluator vs asking rent + advance norms (pure stdlib)
  deals/offers_router.py  offer send/counter/check/accept (terms lock)
  models/offer.py    offers table (structured fields, status)
  agreements/duty.py        stamp-duty band from annual rent (pure stdlib)
  agreements/advisories.py  hedged e-stamping/registration/police advisories
  agreements/render.py      agreement + police-form HTML; WeasyPrint PDF (lazy import)
  agreements/router.py      /deals/{id}/agreement, /pdf, /police-verification-form, /sign
  models/agreement.py       agreements table (terms JSONB, pdf_path, duty band)
tests/               unit tests (local) + DB/Redis-backed flow tests (Docker)
```

> **Schema note:** the app applies Alembic migrations on boot (`alembic upgrade head`), so
> schema changes no longer need a dev-DB wipe — see "Post-MVP hardening" below.

## Web app (M9)

```
web/  Next.js App Router + Tailwind (earthen theme), proxies /api/* -> FastAPI
  app/page.tsx              home: LIVE listing search + filters
  app/listings/[id]         listing detail + Rehnuma ask panel
  app/rehnuma               standalone Rehnuma chat
  app/verify                phone OTP -> CNIC verification
  app/deals, deals/[id]     deal list; chat, offer builder + "Fair?", contact gate, agreement
  app/list-property         owner: create + publish a listing
  lib/                      api client, auth context, types, format helpers (+ unit tests)
```

Run web tests / build: `cd web && npm install && npm test && npm run build`.

## Status: M1–M10 complete

The full MVP per [CLAUDE.md](CLAUDE.md) build order is implemented and tested
(114 backend tests + web unit tests/build). The §8 acceptance flow works end-to-end in the UI.

### Post-MVP hardening (done)
- **DB migrations (Alembic).** The app applies `alembic upgrade head` on boot — schema changes
  no longer need a dev-DB wipe. Migrations live in [alembic/versions/](alembic/versions/);
  generate new ones with `docker compose run --rm -v "$(pwd)/alembic:/app/alembic" api alembic
  revision --autogenerate -m "<msg>"`. (Tests still bootstrap via `create_all` for speed.)
- **Phone encryption-at-rest.** The raw phone is Fernet-encrypted in the DB (key derived from
  `PHONE_ENCRYPTION_SECRET`); decrypted only at the consent-gated contact reveal.
- **Durable PDF storage (MinIO).** Agreement + police-form PDFs are stored in MinIO
  (S3-compatible, self-hosted in compose) instead of the container filesystem — they survive
  restarts and scale across instances. Console at http://localhost:9001 (rehnuma / rehnuma-secret).

### Importing listings via Apify
Scrape towns/flats/houses with an Apify Actor and upsert them as listings (deduped by
`external_ref`). Server-side token only; imports are demo data (they bypass the verified-owner
flow — rule 2).

```bash
# In .env:
APIFY_TOKEN=apify_api_...
APIFY_ACTOR_ID=username~some-zameen-scraper          # an Actor from the Apify store
APIFY_RUN_INPUT_JSON={"startUrls":[{"url":"https://www.zameen.com/Rentals/Rawalpindi-41-1.html"}],"maxItems":50}

docker compose up -d api
docker compose run --rm api python -m app.jobs.apify_import   # run actor -> normalize -> upsert
```

Pipeline: [app/integrations/apify.py](app/integrations/apify.py) (client) →
[app/integrations/normalize.py](app/integrations/normalize.py) (tolerant item→Listing mapper) →
[app/jobs/apify_import.py](app/jobs/apify_import.py) (idempotent upsert). Schedule the job via
OpenClaw for periodic refresh.

### Enabling real Rehnuma answers
Compose passes LLM keys through from the host env / a root `.env` (default empty → safe
fallback). Drop one in and recreate the api container:

```bash
echo "GROQ_API_KEY=gsk_..." >> .env      # free tier; or GEMINI/OPENROUTER/ANTHROPIC
docker compose up -d api
```

The router picks it up automatically (Groq → Gemini → OpenRouter → Anthropic). Keys stay server-side.

### Still deferred
- **Real possession registry** — the Bahria grid is structured-synthetic; swap before production.

### Out of scope for v1 (per CLAUDE.md s.9)
Payments/gateway · e-stamping API integration (advisory only) · cities beyond Bahria ISB ·
tenant screening · owner analytics · vector search/RAG · any "agent" role.
