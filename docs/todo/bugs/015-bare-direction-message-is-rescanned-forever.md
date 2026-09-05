# 015 — A bare-direction message is re-parsed on every scan cycle, forever

**Status:** found 2026-08-28 from live demo-session logs. **Log half fixed
2026-08-28. Rescan half fixed 2026-09-05 — but NOT the way this file
proposed, because that fix would have cost a trade; see *The rescan, fixed*
at the bottom.** What is left is a behaviour question, now in
[docs/simon-handover/027](../../simon-handover/027-what-should-a-direction-only-message-do.md).
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

---

## The rescan, fixed — 2026-09-05

The message is no longer re-parsed. `classify_and_parse` remembers, in
process, the messages it has already classified as a bare direction and
returns early on the next sighting, so none of the six parsers this file
complains about runs a second time.

### Why the suggested fix above was NOT built

Both of its premises turned out to be false when checked against the code,
and the second is a money-path regression.

**"The follow-up path already keys off `tg_message_id`, so a parked row also
gives the later full-levels message something to complete."** It does not.
`second_message_repo.attach_followup_levels()` selects from
`vantage_second_message_holds WHERE status='waiting' AND levels_json IS NULL`.
It never reads `vantage_tg_signals`. A row parked there is invisible to the
follow-up matcher, so the parking would buy nothing on that side.

**A parked row would lose a trade.** `scan_messages.py`'s dedup probe sends
*any* message that already has a row into `_handle_signal_edit_impl`. In there,
an edit that adds full levels to a row is only executed when the row's status
is `pending_followup`: that is the single branch that sets `_promote_execute`.
A row parked as `bare_direction_parked` takes the other branch — fields
updated, `return None`, caller moves on — and the signal is never traded.
Today, with no row at all, that same edit is parsed fresh and taken. So the
tidy-up would silently convert a taken trade into a missed one.

Parking it as `pending_followup` instead is not a way out: that status means
"direction and entry known, levels awaited", and a bare direction has no entry.
It would also make the message eligible for the promotion path on any edit,
which is a real behaviour change to signal parsing.

### What was built instead

A read-only guard, placed **after** the learned-rules parser and the
second-message block and before everything else:

```python
if _is_known_bare_direction(tg_id, text):
    return None
```

- **Keyed on the id AND the message body**, stored as a short digest. A
  Telegram edit keeps the id and changes the text, and that is the usual way
  one of these becomes a real signal. Keying on the id alone would skip the
  edited body forever — the exact trade loss described above, arrived at from
  the other direction.
- **Below the learned-rules parser**, because the operator can add a rule at
  any moment and it must apply to a message already parked.
- **Below the second-message block**, because a levels-only follow-up is a
  different message that still has to be consumed.
- **Read-only.** It must not record, or the first sighting would suppress its
  own log line. The recording still happens where it always did, at the
  bare-direction branch.
- Same bounded, insertion-ordered memory as the log suppression, evicting
  oldest-first.

Nothing is written to the database, no status is invented, and the money path
is untouched.

### Proof

Ten tests in `tests/core/test_bare_direction_rescan_work.py`, the two that
matter watched failing first, plus the seven existing ones in
`test_bare_direction_log_spam.py` still green.

Six mutants, all killed — but **one survived the first attempt and the test
was strengthened rather than the result accepted**: moving the guard above the
second-message block changed nothing, because the follow-up test used a
message that had never been parked, so the guard never fired for it. The test
now parks the message first. Worth recording, because a test that passes in
both positions is not testing the position.

| Mutant | Killed by |
|---|---|
| the guard removed (the bug itself) | 2 tests |
| memory keyed on the id alone | 2 |
| the read-only probe records, so the first sighting self-suppresses | 4 |
| guard moved above the learned-rules parser | 1 |
| guard moved above the second-message block | 1 (after strengthening) |
| eviction drops the newest instead of the oldest | 1 |

### Still open

The message is still not RECORDED, so nothing on screen shows that a
direction-only message arrived and nothing tells you if the follow-up never
comes. That is a behaviour decision, and it is now
[docs/simon-handover/027](../../simon-handover/027-what-should-a-direction-only-message-do.md)
with three options and a recommendation. The in-process memory is also
forgotten on restart, which costs exactly one re-read per parked message —
noted rather than fixed, since persisting it is the same decision.
