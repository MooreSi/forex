# 038 — The bias-gate refusal printed a false comparison and named the wrong rule

**Status:** FIXED 2026-09-09, test-first, **confirmed live at 19:00:19**.
Found while verifying demo 13.
**Money:** no, but it is the only visible evidence that a money gate is working.

## What it printed

Six times between 16:41 and 18:06, on real refusals:

```
[RE-Engine] bias gate blocked live exec RE-2A2BA7 -- htf now bullish vs
direction=SELL, level_score=0.95 < 0.75
```

**0.95 is not less than 0.75.**

## Why

Two different rules share that branch:

1. `_gov.htf_bias_blocks` — the owner's **Only trade with the trend** gate,
   turned on 2026-09-09. It ignores `level_score` entirely.
2. the original level-score bypass, which refuses a counter-bias signal only
   when `level_score < 0.75`.

The message hardcoded the second one's reason onto both. Every one of the six
refusals above came from the owner's gate, so each printed a comparison that is
false and credited a rule that had not fired.

## Why it mattered more than the wording

These lines are the only place the trend gate's work is visible. Reading them,
the natural conclusion is that the level-score bypass is doing the refusing and
the owner's gate is not running.

That is very nearly the conclusion reached while verifying demo 13: searching
the log for the governor's own sentence (`Higher-timeframe bias is ...`)
returns **nothing**, because the Reversal Engine logs its own line. The gate
had refused six trades and looked, from the log, like it had refused none.

## Fixed

`htf_bias_blocks` already returns a sentence naming itself and the setting that
controls it. That sentence is now what appears, with the level-score reason
used only when the level-score rule is what fired. Confirmed in production:

```
19:00:19 [RE-Engine] bias gate blocked live exec RE-A7C5C8 -- htf now bullish
vs direction=SELL: Higher-timeframe bias is bullish — a SELL runs against it.
(Trading > Strategy > Risk Settings: 'Only trade with the trend')
```

Pinned by `tests/reversal_engine/test_bias_block_log_names_the_rule.py`, which
also asserts both rules still refuse — the gate itself was not touched.
