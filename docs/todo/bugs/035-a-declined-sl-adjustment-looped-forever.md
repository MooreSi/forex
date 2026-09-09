# 035 — A declined SL adjustment was re-parsed once a second, forever

**Status:** FIXED 2026-09-09, test-first, mutation-tested. Found by running
demo 17 against the demo account.
**Money:** no. No stop was moved and no order was placed. It burns CPU and
fills the log, and it is a plausible contributor to
[030](030-the-apps-own-event-loop-stalls-are-unexplained.md).

## What happened

With **Enable SL Parsing** off, the decline added by
[034](034-sl-parsing-off-still-moved-an-open-trades-stop.md) worked exactly as
designed, and then repeated:

```
15:49:51 [GOLD DIGGERS INSTITUTIONAL] SL adjustment (tg_id=29402,
         via=learned_rule) to 4391.00 DECLINED — Enable SL Parsing is off
15:49:52 ... identical
15:49:53 ... identical
```

**4,099 identical lines in 71 minutes**, one a second, across five message ids.
Still climbing when it was caught.

## Cause

`try_claim_sl_adjustment` is the dedup that marks a message handled. The
decline `return`ed **before** it, so `scan_messages` offered the same message
on every pass and the decline ran again. This is a regression from 034, made
earlier the same day: before it, the toggle was ignored, the adjustment was
applied, and the claim happened.

## The decision it reverses

`test_sl_parsing_off_blocks_adjustments.py` asserted the message must NOT be
claimed, reasoning that the instruction could still be honoured if the toggle
were switched back on while the message sat in the buffer.

The live run priced both sides. The loop is continuous and certain; the
mid-buffer toggle flip is speculative. The claim now happens first, on both
paths. The old test was **rewritten rather than deleted**, so the reversal and
its evidence stay visible.

**The decline behaviour is unchanged** — no stop is moved, nothing is
substituted. Only the claim moved ahead of the toggle check.

## Pinned by

- `tests/trading/test_declined_sl_adjustment_is_not_retried_forever.py` — the
  loop itself, reproduced as "declined twice for one message".
- `tests/trading/test_sl_parsing_off_blocks_adjustments.py` — the reversal.

Mutation: restoring the original order (claim after the decline) fails three
tests.

## Still open, related

`[PendingWatcher] Signal ... skipped — Filled too soon` repeats the same way
(372 occurrences), once a second until the 300s window passes. That one is
self-limiting rather than unbounded, so it was left alone, but it is the same
shape and the same noise.
