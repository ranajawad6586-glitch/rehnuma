"""DATABASE_URL normalization — hosted Postgres URLs must survive the asyncpg driver."""
import pytest

from app.dburl import SSLMODE_TO_ASYNCPG, normalize_database_url as norm


def test_render_style_postgres_scheme_becomes_asyncpg():
    assert norm("postgres://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"


def test_postgresql_scheme_becomes_asyncpg():
    assert norm("postgresql://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"


def test_already_asyncpg_url_is_not_double_prefixed():
    assert norm("postgresql+asyncpg://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"


def test_neon_url_translates_sslmode_and_drops_channel_binding():
    got = norm("postgresql://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require")
    assert got == "postgresql+asyncpg://u:p@ep-x.neon.tech/db?ssl=require"


@pytest.mark.parametrize("mode", sorted(SSLMODE_TO_ASYNCPG))
def test_every_libpq_sslmode_maps_to_an_asyncpg_value(mode):
    assert norm(f"postgresql+asyncpg://h/db?sslmode={mode}") == \
        f"postgresql+asyncpg://h/db?ssl={SSLMODE_TO_ASYNCPG[mode]}"


def test_unknown_sslmode_falls_back_to_require_not_passthrough():
    # Passing an unrecognised mode through would reach asyncpg and fail the connection.
    assert norm("postgresql+asyncpg://h/db?sslmode=weird") == \
        "postgresql+asyncpg://h/db?ssl=require"


def test_other_query_params_are_preserved():
    got = norm("postgresql://u:p@h/db?sslmode=require&application_name=rehnumarent")
    assert "application_name=rehnumarent" in got and "ssl=require" in got


def test_url_without_query_is_untouched():
    assert norm("postgresql+asyncpg://h/db") == "postgresql+asyncpg://h/db"


def test_password_with_special_characters_is_preserved():
    raw = "postgres://u:p%40ss%3Aword@h/db?sslmode=require"
    assert norm(raw) == "postgresql+asyncpg://u:p%40ss%3Aword@h/db?ssl=require"


def test_local_docker_compose_url_is_unchanged():
    url = "postgresql+asyncpg://rehnuma:rehnuma@localhost:5432/rehnuma"
    assert norm(url) == url


def test_pooled_neon_host_disables_the_prepared_statement_cache():
    # PgBouncer transaction pooling + asyncpg's statement cache => "prepared statement exists".
    got = norm("postgresql://u:p@ep-x-pooler.c-3.aws.neon.tech/db?sslmode=require")
    assert "prepared_statement_cache_size=0" in got and "ssl=require" in got


def test_direct_host_keeps_the_statement_cache_enabled():
    got = norm("postgresql://u:p@ep-x.c-3.aws.neon.tech/db?sslmode=require")
    assert "prepared_statement_cache_size" not in got


def test_explicit_statement_cache_setting_is_not_overridden():
    got = norm("postgresql://u:p@ep-x-pooler.aws.neon.tech/db?prepared_statement_cache_size=50")
    assert got.count("prepared_statement_cache_size") == 1
    assert "prepared_statement_cache_size=50" in got
