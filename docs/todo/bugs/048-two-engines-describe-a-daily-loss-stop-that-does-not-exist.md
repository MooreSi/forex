# 048 — Both research engines advertise a daily loss stop that is not implemented

**Status:** found 2026-09-12, auditing every adaptive parameter for a reader
after bugs/045. **Not fixed** — see the bottom; the honest fixes are a
deletion the owner should agree to, or a new protective limit, and the second
is not an unattended change.
**Touches money:** not today. Neither engine has live execution on, and real
orders are covered by the app-level daily-loss halt, which does work. It
matters the moment either engine's live switch is turned on.
**Severity:** a stated protective limit that does not exist is worse than no
limit, because it is believed.

## The claim

Both engines' parameter catalogues carry this, with a worked rationale:

`test_signal/adaptive_params.py`:

> `daily_loss_stop_usd` — *"Stop generating new signals for the rest of the UTC
> day once today's closed PnL reaches this loss — prevents one hostile day from
> compounding (Jul 6: -$586)"*

`breakout_signal/adaptive_params.py`:

> `daily_loss_stop_usd` — *"Stop generating new signals for the rest of the UTC
> day once today's closed PnL reaches this loss (Jul 2 ran to -$457
> unchecked)"*

Both cite a specific day that a specific limit would have prevented. Both are
rendered as a row on their engine's parameters panel. Both default to $200.

## It is read by nothing

```
grep -rn "daily_loss_stop_usd" backend frontend tests --include="*.py"
  backend/src/services/breakout_signal/adaptive_params.py:166   <- the catalogue
  backend/src/services/test_signal/adaptive_params.py:76        <- the catalogue
```

Two definitions, zero readers. Neither engine checks the day's realised P&L
anywhere; there is no `daily_loss` anything in either package. The days it
names would run exactly the same way today.

## What DOES exist, so this is not a hole in the account

`risk/governor.apply_daily_loss_halt_on_close` is real, runs on the close path
and halts live trading. It covers every real order regardless of which engine
produced it, and it fired repeatedly on this account (visible in the Reversal
Engine's own `live_exec_status` values: *"Trading paused until 22:00 — MT5
order blocked: Daily loss limit hit"*).

So the missing piece is the per-engine one: an engine that has had a bad day
keeps generating and keeps filling its own virtual ledger. That costs nothing
while its live switch is off — which is where both of these are today
(`sg_live_execution` 0, `bo_live_execution` 0).

## The second one, same audit

`test_signal`'s `hour_filter_enabled` is dead in the same way:

> *"Enable the measured toxic-hour block (UTC 07,12-16,20 — combined -$1,377
> across all history). 0 = trade all hours"*

Nothing reads it either — **and the Breakout engine already deleted its copy**,
on 2026-07-16, leaving a note that says exactly why this matters:

> *"removed — it was dead code (defined here but never read anywhere; the real
> toxic-hour gate is the `hour_blocklist_enabled` risk setting checked in
> `_execute_live`). **The nightly AI tuner had set it to 0 believing it was
> disabling a filter.**"*

That is the same failure as bugs/045's `allow_asian`, found and fixed on one
engine two months ago and never carried across to the other. `hour_filter_enabled`
is not tuner-locked on the Bounce engine, so its tuner can still spend a
decision on it, and still believe it has switched something off.

`daily_loss_stop_usd` IS tuner-locked on the Breakout engine and is NOT on the
Bounce one — so the same parameter, dead in both, is protected from the tuner
in one and exposed in the other.

## Why nothing was changed

Deleting a catalogue entry is behaviourally free — nothing reads these — but it
changes the prompt the nightly tuner is given, and that is an LLM whose outputs
decide `min_quality_score`, which has already driven one engine to sixteen days
of silence (`docs/simon-handover/034`). Changing its menu unattended is the
thing that was deliberately not done for `allow_asian`, and consistency is
worth more here than the tidy-up.

## The decision

1. **Delete both entries from the Bounce catalogue** (and
   `daily_loss_stop_usd` from Breakout's), following the July precedent. The
   levers do nothing; the descriptions are the only harm they do.
2. **Implement the daily loss stop** — a real per-engine check before
   generating, using the engine's own closed P&L for the UTC day. This is a new
   protective limit on a signal path and wants a spec and a demo.
3. **Leave them and lock them to the tuner**, if the intent is to implement
   later and the descriptions are wanted as a placeholder. Cheapest, and the
   least honest of the three.

Whichever, a scan asserting that every entry in a `PARAMS` catalogue is read
somewhere would have caught two of these on the day they were written. **That
gate now exists**: `tests/refactor/test_every_tunable_is_read.py`, shrink-only,
with the three known-dead entries listed and each pointing at its bug. Adding
to that set is the regression it stops.

It would NOT have caught `allow_asian` (bugs/045), and the file says so rather
than implying otherwise: that one has a reader, and what is wrong with it is
that nothing calls the reader. Finding that needs a call graph, not a grep.

## Related

* `docs/todo/bugs/045` — `allow_asian`, the same shape, found first.
* `docs/simon-handover/034` — what the tuner did to `min_quality_score`, which
  is why its prompt is treated as a money-path input.
