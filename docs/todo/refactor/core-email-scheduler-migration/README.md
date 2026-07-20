# Core Email Scheduler Migration

Extracts `SimulationEngine._email_scheduler_loop`'s per-cycle body
(core/engine.py) into a standalone module. Seventh pack of the
background-loops cluster in the "finish everything off" push, continuing
from `core-gd-copy-research-migration`.

Checked every minute (after a 60s startup delay, both left as the thin loop
shell in `engine.py`, same split precedent as every prior sweep-style
pack): bails out immediately if no email provider is configured (any one of
`smtp_host`/`resend_api_key`/`mailjet_api_key` -- checking `smtp_host` alone
used to silently skip this whole loop, ORB report included, on a node
configured for Resend/Mailjet with no SMTP host set at all -- confirmed
live on the VPS). Three independent sections follow, each with its own
dedup gate via `app_config`:

1. **Morning ORB report** -- fixed 08:15 Europe/London, weekdays only,
   checked every cycle regardless of the daily/weekly send-time gate below.
   Email and auto-execute are separate toggles (`email_config` vs
   `vantage_risk_settings`) sharing one report/dedup gate -- the report is
   only built once and reused by whichever toggle(s) are on. Reuses the
   already-extracted `core_orb_report.build_orb_report`/`orb_auto_execute`
   as collaborators rather than re-deriving them. This section has its own
   inner `try`/`except` -- a failure here must not prevent the daily/weekly
   sections below from running.
2. **Daily summary** -- configurable `send_time` (default 18:00,
   **server-local time via bare `datetime.now()`**, not Europe/London like
   the ORB section -- an observed inconsistency, not changed during this
   no-behavior-change extraction), weekdays only, gated to the
   active-trader node only (the passive/standby node has no locally-closed
   trades of its own -- confirmed live: both nodes used to send a daily
   summary, one of them always blank). Queries today's locally-closed
   trades, computes performance via the already-extracted
   `core_mt5_performance.compute_mt5_performance`, and asks Claude for a
   narrative analysis (best-effort -- a failure here doesn't block the
   email, just omits the analysis section).
3. **Weekly summary** -- Fridays only (`weekday() == 4`), same
   active-trader-node gate, same `send_time` gate as daily (both share one
   `now.hour`/`now.minute` check -- if it doesn't match, BOTH sections are
   skipped for the whole cycle, not just daily).

See `PROGRESS.md` for task status.
