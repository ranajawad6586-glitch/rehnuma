# RehnumaRent — demo accounts (login cheat-sheet)

Log in at http://localhost:3000 → **Log in / Sign up** → enter the phone → the OTP code shows
on-screen (dev mode). All accounts below are already CNIC-verified.

## Owners (have listings)

| Name | Login phone | User id |
|------|-------------|---------|
| Bilal Khan | `03001110001` | 1 |
| Sana Ahmed | `03001110002` | 2 |
| Imran (Bahria) | `03100000001` | 3 |
| Hina (Bahria) | `03100000002` | 4 |
| Kashif (Pindi) | `03100000003` | 5 |
| Imported (Apify) | `03009000000` | 6 |

## Tenants

| Name | Login phone |
|------|-------------|
| Ali Raza | `03005550101` |
| Sara Khan | `03005550102` |
| Usman Tariq | `03005550103` |
| Ayesha Malik | `03005550104` |
| Bilal Ahmed | `03005550105` |

## Deals already in progress

- **deal #1** — Ali Raza ↔ owner — **ACCEPTED**, agreement generated (rent Rs 104,500)
- **deal #2** — Sara Khan ↔ owner — **ACCEPTED**, agreement generated (rent Rs 41,800)
- deals #3–#5 — Usman / Ayesha / Bilal — open chat (CHAT_OPEN)

## Notes

- ~69 LIVE listings (4 demo + 40 curated Rawalpindi + 25 real Zameen imports via Apify).
- Tests run against a separate `rehnuma_test` database, so running the suite no longer wipes
  this demo data. Re-seed anytime:
  `docker compose run --rm api python -m app.seed_demo && docker compose run --rm api python -m app.seed_scraped`
