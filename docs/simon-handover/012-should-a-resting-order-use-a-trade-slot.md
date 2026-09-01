# Q012 — Should a resting pending order use up one of your trade slots?

**Who answers:** Simon. This is a trading-exposure question, not a technical
one.
**Status:** **ANSWERED 2026-08-31 — A.** Resting orders stay free; only
positions count against `max_open_trades`. That is what the code already did,
so nothing changed. Full answer at the bottom of this file.
**Raised:** 2026-08-30, while closing the risk-gate race (stage1 phase2/030).

## The situation

`max_open_trades` limits how many trades can be **open** at once. Yours is
currently 5.

Since 2026-08-29 the limit is enforced atomically: a signal cannot be claimed
for opening unless a slot is free, counting both open trades and other signals
currently mid-open. That closed a real race where two signals arriving together
could both slip past the cap.

**Resting pending orders are not counted.** The Reversal Engine's limit-order
path places an order that sits on the broker's book waiting for price to reach
it. It claims the signal, but never goes through the cap.

## Why it matters

With a cap of 5, the app could place 5 resting orders while holding 0
positions. If price then moves through all five levels, you end up with **5
open positions**, which is the cap — fine. But it could equally place 5 resting
orders *while already holding 3 positions*, and if all five fill you are at 8.

The orders expire after 60 minutes if unfilled, so the window is bounded. It
has not been observed happening. It is a gap in the arithmetic rather than a
bug anyone has hit.

## Options

- **A. Leave it (current behaviour).** Resting orders are free; only positions
  count. Simplest, and the cap keeps meaning "positions I hold". Risk: a burst
  of signals can overshoot the cap if they all fill.
- **B. Count a resting order as a used slot.** The cap becomes "positions plus
  committed intent", so you can never overshoot. Cost: five resting orders that
  never fill would block all new trading for up to an hour.
- **C. Count them, but with a separate, larger limit** — e.g. max 5 open, max 8
  including resting. More faithful, more to configure.

The trade-off is genuinely two-sided: **A** can overshoot your position limit;
**B** can stop you trading because of orders that never filled.

**ANSWER: A** (owner, 2026-09-01) — resting orders stay free; only positions
count toward `max_open_trades`. No code change; this is current behaviour.

Recorded rather than just closed, because the trade-off is real: a burst of
signals whose resting orders all fill can still overshoot the position limit.
If that is ever observed, this is the decision to revisit, and option C (a
second, larger limit including resting orders) is the middle ground.

## What was fixed regardless

A real defect either way, and mine: this claim path did not record *when* it
claimed. The stranded-claim sweep releases any claim with no recorded time, so
a Reversal Engine order still in flight was being released back into the queue
on the next reconciliation pass — and the signal could be opened twice. The
sweep was causing the exact failure the claim exists to prevent.

It now stamps the claim time, and there are three tests covering the
interaction: a fresh claim is not swept, an abandoned one still is.
