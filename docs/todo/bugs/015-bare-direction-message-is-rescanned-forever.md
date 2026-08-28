# 015 — A bare-direction message is re-parsed on every scan cycle, forever

**Status:** found 2026-08-28 from live demo-session logs. **Log half fixed
2026-08-28; the rescan itself is still open and needs the owner.**
**Touches money:** no. Nothing is executed. This is wasted work and log bloat.
**Severity:** low in effect, high in noise — 3,954 identical log lines from one
Telegram message in 70 minutes.

## What happens

`scan_parse_classify.py:182` handles a message that is a bare direction trigger
("XAU USD BUY", "Sell Zone Now") with no entry, no SL and no TP. It logs and
returns `None`:

```python
if _ime_trigger:
    log.info("[%s] Bare direction tg_id=%s (%s) — silently skipped "
             "(awaiting follow-up with full levels)", ...)
    return None
```

Every other terminal branch in that function records something: a partial
inserts a `pending_followup` row, an unrecognised message goes on the queue, an
unsupported currency gets its own row. This branch records nothing at all.

Nothing marks the message as seen, so the next scan cycle picks it up and does
exactly the same thing, about once a second, for as long as the message stays
inside the reader's fetch window.

## Observed

Gold Diggers VIP, `tg_id=19886`, a 15-character bare SELL:

```
first  2026-08-28 16:41:22,027   (1 ms after the message arrived)
last   2026-08-28 19:06:53       (still going, checked again later)
count  8,319 identical lines and counting
```

Nothing else in the app noticed. No `vantage_tg_signals` row exists for 19886,
which is correct behaviour, and it is also why the loop never ends.

Re-checked 19:06:53 the same evening: still the same single message, still
about one line per second, 8,319 lines. It does not stop on its own -- the
message stays inside the reader's fetch window indefinitely because nothing
ever records it as handled.

`forex_trader.log` is 47 MB. A steady drip of one line per second per parked
bare message is a meaningful share of that.

## Why it is not just cosmetic

The re-parse runs the Format A/B parser, the GD2 parser, both partial parsers
and both instant-entry parsers against the same text every cycle. Cheap
individually; it is the "forever" that makes it worth fixing.

It also hides the thing the log line is for. If a genuine follow-up never
arrives, the operator wants to see that once, not 4,000 times.

## Suggested fix (not applied)

Record the message the way every sibling branch does — insert a
`vantage_tg_signals` row with a status such as `bare_direction_parked` — and log
only on insert. The follow-up path already keys off `tg_message_id`, so a
parked row also gives the later "full levels" message something to complete,
which is what the log line claims is being awaited.

Log-only suppression (remember the id in memory) would fix the noise and not
the repeated work, and would forget across a restart.

This is on the signal-parsing path, so it wants a test written first showing
the second scan of the same message does nothing.

## How it was found

Watching the log for a bare Telegram signal during the M2 demo verification.
The message under observation turned out to be its own separate finding.

---

## What was fixed, and what was not

**Fixed:** the repeated logging. `_note_bare_direction()` in
`scan_parse_classify.py` remembers the message ids it has already logged, in an
insertion-ordered map bounded at 512, and the branch logs only on first
sighting. Eviction drops the oldest, since dropping the newest would restore
the every-cycle spam for the message currently in the window -- the exact case
this exists for.

Behaviour is otherwise unchanged: the message is still skipped, still returns
None, still is not queued as unrecognised. A test asserts that explicitly, so
"only the logging changed" is checked rather than claimed.

**Not fixed, and still needs you:** the message is still re-parsed on every
scan cycle. Stopping that means RECORDING it -- a `vantage_signals` row with a
status such as `bare_direction_parked` -- and that changes signal-parsing
behaviour, including what the follow-up matcher can find. The suggested fix
above stands; it is a decision about how a bare direction should be treated,
not a cleanup.

So the log is readable again, and the wasted work is still there, waiting on
that decision.
