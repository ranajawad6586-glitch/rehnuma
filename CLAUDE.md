# CLAUDE.md — RehnumaRent

> Single source of truth for the RehnumaRent build. Claude Code reads this file first, every session. If something is not in this file, it is not a requirement — ask before inventing it. One milestone per session, explicit acceptance criteria, no scope creep.

---

## 0. What this is

RehnumaRent is a **direct-to-deal rental platform for Bahria Town Islamabad** that removes the property dealer from the loop. Tenants find plot-verified listings, talk to verified owners directly, negotiate in structured steps, and generate a stamp-paper-ready tenancy agreement — guided by **Rehnuma**, a neutral AI realtor.

**The thesis:** dealer involvement adds cost (one month's rent from each side) and conflict of interest. RehnumaRent replaces the dealer with (a) verification infrastructure, (b) a neutral AI advisor, and (c) a structured negotiation → agreement pipeline.

**MVP scope = Bahria Town Islamabad only.** Chosen because gated, numbered phases/sectors with standardized house categories (5-marla, 10-marla, 1-kanal) and verifiable possession records make listing verification tractable. Do not build for other cities or societies until the Bahria flow is proven end-to-end.

---

## 1. Non-negotiable rules

These are fixed constraints. Do not violate them, do not "improve" past them, do not ask to relax them.

1. **Dealer-free.** No "agent" role, no commission flows, no lead-routing to third parties. Owner ↔ tenant is direct.
2. **Verified-only listings.** A listing does not go live until its plot reference is matched against the Bahria grid AND the owner passes CNIC + phone OTP. No exceptions, no "pending" listings shown to tenants.
3. **Rehnuma is neutral.** The AI advisor never represents one party's commercial interest over the other. Either side can invoke it. It works "for the deal, not a commission." This framing is load-bearing for trust — preserve it in the system prompt verbatim intent.
4. **Never assert false legal certainty.** Rehnuma and the agreement generator must flag that stamp duty scales with annual rent and that ICT/Punjab may require e-stamping. Never hard-code "Rs 200 is always correct." Compute the duty band from annual rent.
5. **LLM stack: Groq first.** Primary model is Groq `llama-3.3-70b-versatile` (free tier). Fallback chain is fixed: **Groq → Gemini → OpenRouter → Anthropic Haiku**. No LangChain / LangGraph / CrewAI. Plain `httpx` calls + a thin router. No vector DB in MVP.
6. **API keys server-side only.** No LLM key, no third-party key ever reaches the client. All model calls proxy through FastAPI.
7. **CNIC and phone are sensitive.** Store hashed where used for matching; never expose another party's CNIC or raw phone number in the client until both parties consent to share contact.
8. **No payment handling in MVP.** The agreement fee and any deposits are out of scope for v1 — design the schema to allow it later, but do not integrate a payment gateway now.

---

## 2. Stack

Standard house stack. Do not substitute without a reason in writing.

- **Backend:** FastAPI (Python 3.11), Pydantic v2, SQLAlchemy 2.x async
- **DB:** PostgreSQL 16 (+ PostGIS for the Bahria plot grid)
- **Cache / queue:** Redis, Celery for OTP + notification jobs
- **LLM router:** custom `rehnuma_llm.py`, fallback chain per rule 5, `httpx` async
- **Messaging / OTP:** WhatsApp Business API (OTP + deal notifications), SMS fallback
- **Frontend:** Next.js (App Router) + Tailwind. Aesthetic: warm "earthen" — moss `#1f5d4c` / clay `#c2703d` / paper `#f4efe4`, Fraunces display + Outfit body. Deliberately NOT blue-classifieds. Reference the prototype.
- **Agreement PDF:** server-side render (WeasyPrint or Playwright→PDF) sized to Rs 200 stamp-paper layout
- **Deploy:** Hetzner VPS, Docker Compose, Caddy reverse proxy
- **Agent execution:** OpenClaw for scheduled jobs (verification batch, comp-data refresh)

---

## 3. Domain rules (Bahria + Pakistani rental norms)

Encode these as constants / config, not scattered magic numbers.

- **Plot grid:** Bahria Town ISB phases and sectors are a known address space. House reference format e.g. `287-C` within `Sector C, Phase 4`. The verification step matches owner-submitted `{phase, sector, house}` against the seeded grid + possession reference.
- **Advance norm:** 2–3 months advance + 1 month security is normal. **6 months advance is a red flag** Rehnuma must surface.
- **Maintenance dues:** Bahria maintenance dues must be cleared before possession — Rehnuma reminds tenant to confirm.
- **Term:** default tenancy 12 months, adjustable by mutual consent.
- **Notice:** 4 weeks' written notice is the standard termination clause.
- **Stamp duty bands (annual rent → duty):** `≤100,000 → Rs 500`, `100,001–500,000 → Rs 1,000`, `>500,000 → Rs 2,000`. Rs 200 paper genuinely suffices for many short/low-rent informal agreements but is NOT universal — show the computed band.
- **e-stamping / registration:** ICT and Punjab may require e-stamping for 12-month terms; Punjab Rented Premises Act may require registration with the rent registrar; police tenant verification is required. Surface these as advisories with a one-tap "generate police verification form."

---

## 4. Rehnuma — the AI realtor

### Role
Neutral, experienced realtor familiar with both Pakistani tenants and owners. Straight answers, no fluff, no commission bias.

### System prompt (canonical — keep intent, inject live context)
```
You are Rehnuma, an experienced, plain-spoken property realtor inside the RehnumaRent app,
advising on rentals in Bahria Town Islamabad. You are NEUTRAL — you work for a fair deal,
not a commission, and you say so. You understand both Pakistani tenants and property owners
and their typical concerns.

Property in context: {size} house, {sector}, Bahria Town ISB (House {house}).
Asking rent Rs {rent}/month, {beds} beds, {baths} baths.
Market comps you know: {comps}.

Rules:
- Give STRAIGHT, specific answers. Cite the comp range when rent fairness comes up.
- Reply in the user's language: Roman Urdu in → Roman Urdu out; English in → English out.
- Norms: Bahria advance 2–3 months + 1 month security; 6 months advance is a red flag;
  maintenance dues cleared before possession; agreements on stamp paper (Rs 200 common,
  but ICT/Punjab may need e-stamping and duty scales with annual rent); police tenant
  verification required.
- Concise: 2–4 short sentences or a tight bullet list. **Bold** key numbers.
- Never invent legal certainties — flag when something varies.
```

### Behaviour requirements
- Carries conversation history within a session.
- Knows which listing the user is viewing; comps update per listing.
- Detects Roman Urdu vs English and matches it.
- Invokable from: listing detail, the Rehnuma tab, and inside negotiation ("is this offer fair?").
- The "Fair?" check in the offer builder compares the user's numbers to asking price + advance norm and returns a one-line verdict.

### LLM router (`rehnuma_llm.py`)
- Signature: `async def ask(messages, system, *, max_tokens=1000) -> str`
- Try providers in fixed order; on error/timeout (per-call ~8s) fall through to next.
- Log which provider served each call. Never raise to the client — on total failure return a safe canned advisory.

---

## 5. Core flows (state machines)

### Listing lifecycle
`DRAFT → PLOT_SUBMITTED → GRID_MATCHED → OWNER_VERIFIED(CNIC+OTP) → LIVE → (RENTED | EXPIRED | DELISTED)`
Tenants only ever see `LIVE`.

### Deal / negotiation
`INQUIRY → CHAT_OPEN(after tenant CNIC+OTP) → OFFER_SENT → (COUNTERED ↔ OFFER_SENT) → ACCEPTED → AGREEMENT_GENERATED → SIGNED_OFFLINE`
- Offer is structured: `{rent, advance_months, security, duration_months, move_in}` — discrete fields, not free text.
- `ACCEPTED` locks the terms; the agreement is generated only from locked terms.

### Contact privacy gate
Phone numbers / CNIC are hidden until BOTH parties consent. Chat opens after the tenant clears CNIC + phone OTP (protects owners from call-spam → the reason owners default to dealers).

---

## 6. Data model (minimum)

- `users` — id, name, phone (hashed for match), cnic (hashed), role flags (can be both owner & tenant), verified_at
- `plots` — phase, sector, house_ref, geom (PostGIS), possession_ref — seeded reference grid
- `listings` — owner_id, plot_id, size, rent, beds, baths, status, photos, created_at
- `deals` — listing_id, tenant_id, status, locked_terms (jsonb), created_at
- `messages` — deal_id, sender_id, body, type (text|offer|system), created_at
- `agreements` — deal_id, terms (jsonb), pdf_path, stamp_duty_band, created_at
- `ai_sessions` — user_id, listing_id, transcript (jsonb), provider_used

---

## 7. Build order (one milestone per Claude Code session)

Each milestone ships with tests + a runnable demo before the next begins.

1. **M1 — Skeleton.** FastAPI + Postgres + Docker Compose up; health check; seed the Bahria phase/sector/plot grid (PostGIS).
2. **M2 — Auth + verification.** Phone OTP (WhatsApp), CNIC capture (hashed), user records.
3. **M3 — Listings + plot match.** Owner submits listing; grid-match against `plots`; status machine; only `LIVE` exposed to tenant API.
4. **M4 — Rehnuma LLM router.** `rehnuma_llm.py` with Groq→Gemini→OpenRouter→Haiku fallback; system prompt injection; provider logging; safe-fail.
5. **M5 — Rehnuma endpoint + chat UI.** `/ai/ask` proxy (keys server-side); listing-aware context; Roman Urdu handling; transcript persistence.
6. **M6 — Direct chat + privacy gate.** Owner↔tenant messaging; contact hidden until mutual consent; chat opens post-tenant-verification.
7. **M7 — Structured offer engine.** Offer fields, counter loop, "Fair?" check via Rehnuma, terms lock on accept.
8. **M8 — Agreement generator.** Render locked terms → stamp-paper PDF; compute duty band; e-stamping/registration advisories; police-verification form.
9. **M9 — Frontend polish.** Next.js earthen UI matching the prototype; full tenant flow click-through.
10. **M10 — Hardening.** Rate limits, OTP abuse protection, observability, OpenClaw cron for comp-data refresh + verification batch.

---

## 8. Acceptance criteria (definition of done)

- A tenant can: search/filter LIVE listings → open detail → ask Rehnuma (live, Roman Urdu or English, listing-aware) → verify (OTP) → chat owner → send structured offer → on accept, generate a stamp-paper PDF with the correct computed duty band.
- No listing is visible to tenants unless plot-matched AND owner-verified.
- No LLM/API key is ever present in client code or network responses.
- Rehnuma never claims a single fixed stamp value is universally correct.
- Fallback chain demonstrably works: kill Groq, calls still succeed via Gemini.

---

## 9. Out of scope for v1 (do not build)

Payments / gateway · e-stamping API integration (advisory only for now) · cities beyond Bahria ISB · tenant screening reports · owner analytics dashboard · vector search / RAG · any "agent" role.

---

## 10. Session protocol for Claude Code

- Read this file fully at the start of every session.
- State which milestone you are on. Do exactly that milestone.
- If a requirement is ambiguous or missing, ASK — do not invent.
- Write tests with the feature, not after.
- End each session with: what shipped, how to run it, what's next.
