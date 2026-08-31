
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

The second is the one that matters: **I claimed better than reality.** Both
came from writing the message before running the measurement, on the
assumption I could predict the number. Measure first.
