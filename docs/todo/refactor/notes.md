
* in backend src db directory i still see a lot of db migration stuff, i don't expect it to be here, should be using alembic, e.g. migrations.py schema_sql.py etc..
  * → DONE 2026-08-11: moved to `backend/migrations/` (schema_sql.py + registry.py + backfills.py).
    Alembic considered and rejected — no SQLAlchemy to autogenerate against, new installer
    dependency, and the registry already gives ordered/versioned/fail-closed/legacy-tested.
    Decision recorded in docs/system/domains/data/README.md; revisit only if SQLAlchemy arrives.
* how robust are the circuit breakers? are they designed well? can they be improved?