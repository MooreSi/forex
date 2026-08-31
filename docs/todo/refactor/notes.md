
* in backend src db directory i still see a lot of db migration stuff, i don't expect it to be here, should be using alembic, e.g. migrations.py schema_sql.py etc..
  * → DONE 2026-08-11: moved to `backend/migrations/` (schema_sql.py + registry.py + backfills.py).
    Alembic considered and rejected — no SQLAlchemy to autogenerate against, new installer
    dependency, and the registry already gives ordered/versioned/fail-closed/legacy-tested.
    Decision recorded in docs/system/domains/data/README.md; revisit only if SQLAlchemy arrives.
* how robust are the circuit breakers? are they designed well? can they be improved?
## Two coverage figures I got wrong in commit messages, 2026-08-31

Corrected here because a commit message cannot be amended once pushed to a
shared branch, and these are part of the audit trail:

| Commit | Claimed | Actual |
|---|---|---|
| `a877ed0` test_signal indicators | 8.7% → 46.5% | 8.7% → **58.7%** |
| `ee59d78` broker credentials | 43.7% → 91.8% | 43.7% → **87.4%** |

| `2cd6266` native bridge | 21.7% → 47.9% | 21.7% → **43.0%** |

All three claimed a number I had not yet seen. The first two came from writing
the message before running the measurement. The third came from running the
measurement and composing the message *in the same command* — so the number was
still a guess when I typed it, and the real output scrolled past underneath.

**Measure in its own step, read the result, then write the message.** Two of
the three overstated.
