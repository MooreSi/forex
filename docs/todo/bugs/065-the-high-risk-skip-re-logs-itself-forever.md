# 065 — The high-risk skip re-logs itself on every scan cycle, forever

**Status: log half FIXED 2026-09-18, test-first.** Found from the live demo
log while answering "why didn't the app parse the most recent Telegram
signal?". **Touches money:** no. Nothing is executed either way; the skip
itself is unchanged. **Severity:** low in effect, severe in noise — 80% of
one day's log file.

This is [015](015-bare-direction-message-is-rescanned-forever.md) again, in
the branch nobody checked when 015 was fixed. Same cause, same shape, same
fix; the search that found the first one would have found this one.

## What happens

`scan_messages.py:141`, the `exclude_high_risk` gate, drops the message with
`continue`:

```python
if exclude_high_risk and "high risk" in text.lower():
    log.info("[engine] Skipping high-risk signal tg_id=%s", tg_id)
    continue
```

That `continue` is **above** the dedup lookup at line ~187
(`_tg_repo.get_tg_signal_meta(tg_id)`) which is what marks a message as
handled. So nothing records the skip. The message stays in the reader's
fetch window, the next cycle re-decides it identically, and the line is
written again about once a second for as long as it is there.

## Observed

`~/Library/Application Support/ForexTrader/data/forex_trader.log`,
2026-09-18, read at 07:28 — the day was 7.5 hours old:

```
total lines                       255,588
"Skipping high-risk signal"       204,359   (80.0%)
file size                         31 MB
distinct tg_ids cycling           9
oldest one still cycling          1627      (a previous session)
first line of the day             00:00:00,932
```

Nine messages. One of them, `tg_id=1627`, is old enough that it predates the
current run entirely — a parked message does not age out on its own, exactly
as 015 described.

## Why it is not just cosmetic

The runbook's own fault-finding grep (`docs/system/domains/`, and the memory
note that found [061](061-one-typo-in-one-message-stops-the-ref-backfill.md))
works by counting repeated WARNING/ERROR lines. A single INFO line at 80%
volume does not break that grep, but it does break reading the log at all:
every real event today is separated from the next by hundreds of copies of
this one. 061 was found because 25 repeated lines stood out. At 204,359,
nothing stands out.

## The fix

The 015 idiom, copied deliberately rather than invented:
`_note_high_risk_skip(tg_id, text)` — a bounded `OrderedDict` of 512 entries,
keyed on the id **and** a digest of the body, with
`reset_high_risk_log_memory()` as a test seam. First sighting logs; rescans
are silent; an edit that is still high-risk logs once more, because it is a
different decision on different text.

Pinned by `tests/core/test_high_risk_skip_log_spam.py`, written first and
watched fail on the three spam assertions (the other six passed against the
unfixed code, which is correct — they characterise behaviour the fix must
not change).

## What is deliberately NOT fixed

The message is still not recorded as processed, so it is still re-decided
every cycle — the work half, not the log half. Recording it would change
which messages reach the parser on later cycles, including after an edit, and
that is a signal-parsing behaviour change. 015 left the same half alone for
the same reason, and when its rescan half was eventually fixed on 2026-09-05
the obvious version of the fix would have cost a trade. Left to the owner.

## Related, found at the same time, not a bug

The filter is a plain substring match on the whole message body, so a signal
that merely mentions high risk in passing is dropped the same as one labelled
`HIGH RISK TRADE`. Live examples from Gold Diggers VIP on 2026-09-17:
`tg_id=21426` ("lower entry high risk is 4355-4350 Zone") and `tg_id=21427`
("If you took the high risk set up well done"). Neither was a tradeable
signal, so nothing was lost. Whether the filter should match only a label
line is a policy question for the owner, not a defect.
