# Core GD Copy Research Migration

Extracts `SimulationEngine._gd_copy_research_loop`'s per-cycle check-and-run
body (core/engine.py) into a standalone module. Sixth pack of the
background-loops cluster in the "finish everything off" push, continuing
from `core-max-tp-hit-migration`.

Checked every minute (after a 90s startup delay, both left as the thin loop
shell in `engine.py`, same split precedent as every prior sweep-style pack):
once a day at 22:00 Europe/London, gated to the physical local node only
(`is_remote_node()`, not `_is_active_trader_node()` -- the ML model this
enriches is a per-node file, never synced), dedup'd by date via
`app_config["gdc_research_last"]` so a restart near 22:00 can't fire it
twice. Delegates the actual pipeline (reading the day's Telegram messages,
Claude synthesis, ML retrain, email) to
`gd_copy_signal/telegram_research.run_nightly_research(engine)` -- a large,
separate-module dependency that needs the full engine instance, taken here
as an injectable `research_runner` collaborator (same "optional injected
async callable" pattern used throughout this cluster for out-of-scope
dependencies).

Note: `is_remote_node()` is checked on *every* one-minute tick regardless of
the hour/minute gate -- an unconditional DB round-trip 1,440 times a day for
a check that only matters during one specific minute. Not a bug, just an
observed inefficiency; not changed during this no-behavior-change
extraction.

The loop's own `try`/`except asyncio.CancelledError: break` /
`except Exception` stays in `engine.py`'s thin wrapper -- error handling is
at the cycle level here (there's only one "item" per cycle, unlike the
per-trade sweeps), so this is equivalent to the per-trade-exception-handling
packs, just with the exception boundary one level up.

See `PROGRESS.md` for task status.
