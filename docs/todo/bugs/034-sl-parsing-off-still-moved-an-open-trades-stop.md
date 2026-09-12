# 034 — "Enable SL Parsing" off, and a follow-up still moved a live stop

**Status:** **FIXED 2026-09-09**, test-first. **NOT DEMOED** — it declines an
action that previously happened, on an open position's stop loss.
**Money:** yes. It is where the stop sits on a live trade.
**Found:** live, reported by the owner with the toggle off:

```
SL adjusted — GOLD DIGGERS INSTITUTIONAL
Trade 062f91ad (ticket 1969210518): 4391.65 → 4395.0
Source: learned rule
```

## Why the toggle did not cover it

`apply_sl_parsing_override` handles "Enable SL Parsing" when a **new signal's**
stated stop is parsed, substituting a template or fallback distance. It has
nothing to do with this path.

A later message saying "adjust SL to X" is a different category entirely: a
follow-up to a trade that is **already open**. `scan_messages`'s SL-adjustment
fast path matches it with a learned rule and applies it, and never asked
whether stops should be taken from Telegram at all.

**One setting, two meanings of "parse an SL", only one honoured.** The owner's
reading is the plain one: *"sl parsing applies to all telegram channels so this
needs resolving"*.

## The fix, and where it went

Inside `ai_signal_fallback.apply_sl_adjustment` — **not at its call sites**.
Two routes reach that function:

| route | |
|---|---|
| `scan_messages.py` | the learned-rule fast path (what fired here) |
| `ai_signal_fallback.py` | the AI classifier, first time a channel's wording is seen |

Gating each one is how the next route added gets missed. That is bugs/024's
lesson (three copies of the IME gate, one route eventually missed) and
reversal-engine/080's (a trend filter on one route and not the other), and
`20-trading-safety.md` warns about the shape by name.

**OFF means decline, not substitute.** At entry the toggle supplies a distance
because a trade must have a stop; here the trade already has one, so the
instruction is simply refused and logged with the reason.

**Unreadable settings fail OPEN.** Refusing to move a stop because a settings
read failed would leave a trade sitting on a stop the channel has already said
to move — worse than the thing being guarded against.

The check runs **before** the message is claimed. Claiming marks it handled, so
declining and claiming would mean the instruction could never be honoured if
the toggle were switched back on while the message was still buffered.

## Proof

7 tests, red first. Four mutants killed: the gate removed, the default flipped
so an absent column disables adjustments, unreadable settings failing closed,
and the gate moved to after the claim.

## Worth knowing

The scan loop passes the risk settings it already holds, so the gate costs no
extra read per message. A caller without them falls back to reading once.

---

## Live evidence, three days of it (2026-09-12)

The status line says NOT DEMOED. Nobody has watched it decline on a demo
terminal, and that is still true — but the live database now has three days of
it, and they say the right thing.

**The fix landed at 13:52 on 2026-09-09** (`1a849bd`). The account's own tables
either side of that moment:

| | |
|---|---|
| SL adjustments **announced as applied** | **3**, all on 2026-09-09 at 11:38, 12:22 and 13:08 — every one **before** 13:52 |
| SL adjustment messages **claimed** since the fix | **37** (9 on 09-09, 18 on 09-10, 13 on 09-11) |
| SL adjustments announced since the fix | **0** |

`lk_enable_sl_parsing` is `0` on this account and every other `lk_*` parsing
switch is off too, except `lk_enable_close_all_parsing`.

So thirty-seven instructions arrived that would previously have been candidates
to move a live stop, and no stop moved.

**Stated honestly:** the claim rows are written by
`recovered_repo.try_claim_sl_adjustment`, which is a dedup marker taken before
the broker call, not proof of an attempt that was then refused. Some of those
37 will have had no matching open trade at all. What the data does establish is
the part that matters — **after the fix, nothing moved a stop, and before it,
three things did, in the two hours before it landed.**

That is not a substitute for the demo. It is a reason to expect the demo to
pass.
