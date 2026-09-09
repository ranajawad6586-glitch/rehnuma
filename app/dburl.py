"""DATABASE_URL normalization for the asyncpg driver. Pure stdlib — no app imports.

Hosted Postgres providers hand out libpq-style URLs: Render/Heroku use the `postgres://`
scheme, and Neon/Supabase/Aiven append `sslmode=` and `channel_binding=` query parameters.
SQLAlchemy needs the `postgresql+asyncpg://` scheme, and asyncpg accepts neither libpq
keyword — it raises TypeError at connect time — so both have to be translated before the
engine is built.
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# libpq sslmode -> the value asyncpg understands. asyncpg has no CA-verification distinction
# here, so verify-ca / verify-full both collapse to `require`.
SSLMODE_TO_ASYNCPG = {
    "disable": "disable",
    "allow": "prefer",
    "prefer": "prefer",
    "require": "require",
    "verify-ca": "require",
    "verify-full": "require",
}


def normalize_database_url(url: str) -> str:
    """Rewrite a managed-Postgres URL into one SQLAlchemy + asyncpg accept."""
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    parts = urlsplit(url)
    if not parts.query:
        return url

    kept = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "channel_binding":
            continue  # asyncpg negotiates this itself and rejects the keyword
        if key == "sslmode":
            # An unrecognised mode falls back to `require` rather than passing through:
            # anything asyncpg does not know would fail the connection outright.
            kept.append(("ssl", SSLMODE_TO_ASYNCPG.get(value, "require")))
            continue
        kept.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(kept)))
