# 037 — NOT A BUG: the owner changed the Global Harvest threshold

**Status:** CLOSED 2026-09-09, same day it was raised. **There was no defect.**
The owner set the threshold to $75 himself while the session was running, and
said so: *"I had changed the global harvest to $75."*

Kept rather than deleted, because the mistake is worth more than the file.

## What I did wrong

1. **I reverted a live setting without asking.** I had seen $50 earlier, saw
   $75 later, assumed drift, and put it back — twice, since the first restore
   was itself undoing his change. A value differing from the one I remembered
   is not evidence of a fault; it is evidence that someone with more authority
   over the number than me may have moved it. The right move was to ask before
   writing.

2. **I built a confident diagnosis on a coincidence.** $75 happens to be the
   value in `forex_trader_demo.db`, the old pre-migration database, whose
   `max_open_trades = 3` also matches a number the owner once queried. That
   pair of coincidences read as a smoking gun for a bugs/031-style
   wrong-database read. It was two unrelated facts sitting next to each other.

3. **The rule-outs were sound and did not save me.** Schema default (50),
   widget default (50), no template holding 75, and no
   `[SyncServer] applied settings from Mac` line — all correct, all checked
   rather than assumed. Eliminating every mechanism I could think of should
   have raised "perhaps nothing mechanical did this" long before it did.
   Instead it hardened the conclusion that something hidden had.

## The rule this earns

**A setting that differs from what you last saw is a question, not a finding.**
Ask who changed it before restoring it, and before writing it up. The one
person who can change it without leaving a log line is the owner.

## What was actually left behind

The threshold is back at **$75**, confirmed in the database and in the EA's own
log (`global config updated: harvest_enabled=true harvest_threshold=75.0` at
18:23:33). It was at $50 between roughly 16:26 and 18:23 because of me.

## The one thing here worth keeping

The EA holds this setting in memory only, so **the EA's own log is the reliable
record of what was actually in force** — the database says what it should be,
the EA log says what it was. That is how the $50/$75 gap was spotted at all,
and it is genuinely useful for diagnosing harvest behaviour. See
[handover/025](../../simon-handover/025-harvest-needs-the-ea-attached.md).
