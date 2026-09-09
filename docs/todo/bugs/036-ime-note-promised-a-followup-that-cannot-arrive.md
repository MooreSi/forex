# 036 — The IME note and log line promised a follow-up on template trades

**Status:** FIXED 2026-09-09, test-first. Found by running demo 12.
**Money:** no. Wording only — the stop itself was always correct.

## What happened

Running demo 12 on the demo account, the log said:

```
[IME] Instant BUY executed @ 4416.27 lot=0.10 ticket=1970437618 SL=4411.33 (provisional)
```

and the note stored on the signal row said:

```
Instant market entry — provisional SL $4411.33 (5.0 pts = -$50 max)
— awaiting follow-up SL/TP (tg_id=20813)
```

The runbook's fail condition for demo 12 is, in terms, *"the words 'awaiting
follow-up' on a template-managed channel"*. So the demo read as a failure.

**It had passed.** `5.0 pts` IS the governing template's `sl_pips=50`
(`use_dynamic_atr` is 0), and the Telegram alert correctly said
`(SL from template "30 TP1 SL50 and Trail")`. bugs/023 fixed the alert and left
these two.

The stop distances varying between 4.82 and 6.02 across the day is fill
slippage between the quoted entry the SL is computed from and the actual fill,
not the template being ignored.

## Why it matters despite being cosmetic

`instant_followup.py`'s `managed_by == "ea"` skip means a template-managed trade
**never** receives a follow-up SL/TP. The promise structurally cannot be kept,
and the note is what someone reads back in the Pending Signals panel and in any
later investigation. It cost about twenty minutes of investigation here, into a
system that was working.

## Fixed

Both the stored note and the log line are now template-aware, matching what the
Telegram alert has said since bugs/023. Non-template trades are unchanged --
for those a follow-up genuinely can arrive.

## Honest limitation of the tests

`tests/trading/test_ime_template_note_does_not_promise_a_followup.py` reads
source text, so it cannot see reachability. Making the template branch
`if False:` kills only one of its four tests. That was measured, not assumed,
and is recorded in the file. A behavioural test would need
`execute_instant_entry` driven end to end with a template bound; it is worth
doing if this wording ever matters more than it does today.
