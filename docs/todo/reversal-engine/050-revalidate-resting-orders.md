# 050 — Re-check a resting order before it fills

**Status:** open, **after [040](040-filter-the-instant-fills.md)**, whose rule
it shares.
**Money:** yes — it cancels orders that would otherwise fill.
**Raised by the owner, 2026-09-08:** *"if there are pending/resting trades
before they execute re-evaluate whether they are still valid to ensure they
should still be executed based on market conditions"*.

## Correct in principle, smaller than it looks

The measurement in 040 shows staleness costing little: over 60 minutes is
-$214 across 54 trades, against -$2,023 for the instant fills. So this is worth
doing and it is **not** where the money is.

## Part of it already exists

`reversal_engine_live_execute.py` already re-evaluates `ml_prob` at fill time
and falls back to the creation-time value if that fails — see the
`fill-time re-evaluation failed ... falling back to creation-time ml_prob`
warning. What does not exist is a re-check of whether the LEVEL is still valid.

## The constraint that matters

Use the same rule as 040. One definition of "is this level still valid",
called from both places.
