"""Scheduled jobs, run by OpenClaw (CLAUDE.md s.2). Each is an idempotent, runnable module:

    python -m app.jobs.comp_refresh          # refresh cached market comps
    python -m app.jobs.verification_batch    # expire stale LIVE listings
"""
