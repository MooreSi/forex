# 061 — One typo in one message stops the whole REF backfill

**Status: the containment is FIXED (test-first, 2026-09-16). The parser half
is NOT fixed and is the owner's call** — see "What I did not change".

Found 2026-09-16 reading the live log for recurring warnings.

## The evidence

`forex_trader.log`, once an hour, every hour, since 2026-09-14 15:30:

```
2026-09-16 20:17:32,798 WARNING ...core_ref_signal_backfill —
    [RefBackfill] failed: could not convert string to float: '4284.5.'
```

25 times on the 16th, 24 on the 15th, 9 on the 14th from 15:30 onward. One
line each. Nothing else in the app says anything is wrong.

The string is a real message. `telegram_messages` id 1205040, tg id 1483,
'Gold Diggers Scalping', 2026-09-14T15:30:17Z:

```
Buy Gold Now

4284.5. - 4278.5          <- a typed full stop after the first price

TP 4287
TP 4290
TP 4293
TP 4296
TP open

SL 4274
```

`_GD2_ENTRY_RANGE_RE = ([\d.,]+)\s*[-–—]\s*([\d.,]+)` captures `4284.5.`
including the full stop, and `parser._f` raises `ValueError` on it
(`parser.py:388` -> `parser.py:202`).

## The cost

`backfill_ref_signals` had **one** `try`/`except`, around the entire loop
**and** the single INSERT that follows it. So the ValueError did not skip a
message — it discarded every record built before it and skipped every message
after it, and returned `recorded: 0`.

Replaying the live 72h window against the copied DB:

| | |
|---|---|
| candidate messages in the window | 664 |
| parseable REF signals among them | **15** |
| recorded before the raise | 0 |
| recorded after the fix would be | 15 |

Rows come back `ORDER BY received_at ASC`, so a bad message early in the
window is the worst case, and this one was. That is 15 reference-channel
entries missing from `vantage_tg_signals` for two days, on every pass.

This matters because `reversal_engine_correlate` reads that table, and
REF-correlated signals are the only subset of the Reversal Engine's trades
that does not lose money. The hole this module exists to fill is the hole it
was leaving.

It self-heals on 2026-09-17 15:30, when the message ages out of the 72h
lookback. That is luck, not a fix — the next typo restarts it.

## The fix

A per-message `try`/`except` inside the loop, counting `unparseable` and
naming the message it skipped.

**This guard already existed on the live path.**
`scan_messages.py:468`, with a comment saying exactly this — "One malformed
message must not abandon the whole scan pass" — ported in the 2026-08-25
merge. This module was written 2026-07-31 and never got it. Two paths over
the same parser, one hardened and one not.

## A second staleness in the same function

`parse_stored_message`'s docstring says it "mirrors the parser selection
classify_and_parse makes". It stopped being true on **2026-08-27**, when the
owner directed that parsing rules apply identically to every channel and
`classify_and_parse` stopped branching on `parser_format`
(`domains/signals/README.md`). This module was written 2026-07-31 and still
branched three ways, so:

* a GD2-shaped signal on a `format_ab` channel was recorded live and missed
  here;
* a Format A/B signal on a `gd2` channel, likewise;
* the non-XAUUSD guard sat inside the `format_ab` branch only — the exact
  placement the live path moved out of.

**Measured effect on the live 72h window: none.** Both orderings record the
same 15 signals; each channel's messages currently match its configured
format. Fixed anyway, because the table this writes is meant to be the record
of what the channels said, and a record that disagrees with the live path
about what counts as a signal is a trap for whoever reads it next.

Fixed test-first. `parser_fmt` stays in the signature — callers read it from
the channel config and 'none'/disabled still means a channel is not scanned —
but it no longer selects parsers.

## What I did not change

**`_f` still raises on `4284.5.`**, and a test pins that it does.

Loosening it (stripping a trailing `.` or `,` from a captured number) would
make the LIVE scan parse a message it currently drops, and a parsed Format-B
/ GD2 entry on an enabled channel is executable. That is a change to what the
app can trade, from a code path that reaches `open_trade`. It needs the owner
and a demo session, not a quiet regex widening.

The live scan is not currently losing signals to this: 'Gold Diggers
Scalping' is a reference channel, `_scan_messages` never reached the message,
and there is no `Signal scan failed` line anywhere in the 14th's log. But the
same typo on an **executing** channel would be caught by that path's guard,
logged, and the trade silently not taken.

**Question for the owner:** should a price with a trailing full stop or comma
be read as the number, on the live path as well as this one? Recorded in
`docs/simon-handover/`.

## Tests

`tests/core/test_ref_signal_backfill.py`, three added, two red first:

* `test_the_typo_message_still_raises_in_the_parser` — pins the input, so the
  containment test cannot quietly become an empty branch.
* `test_a_message_the_parser_chokes_on_does_not_lose_the_others`
* `test_a_bad_message_before_every_good_one_still_records_them` — the live
  ordering, which is what took the pass from 15 to 0.

## Mutants

Five, against `tests/core/test_ref_signal_backfill.py`.

| mutant | result |
|---|---|
| the per-message guard removed (the original code) | KILLED, 2 tests |
| `unparseable += 1` -> `+= 0` | KILLED, 2 tests |
| `except Exception` -> `except ValueError` | **SURVIVED** first time |
| channel branching restored | KILLED, 2 tests |
| the currency guard deleted | **SURVIVED**, and stays survived |

The ValueError mutant was a real gap and is now closed. The property being
defended is not "a ValueError is contained" — it is that no failure on one
message abandons the pass, which is the wording the live scan's guard carries.
A parser fed years of arbitrary channel text can raise `TypeError`,
`KeyError` or `AttributeError` just as easily. The new test raises a
`TypeError` through a patched parser and kills it.

The currency-guard mutant survives and **should**: `parse_gold_signal`
refuses a non-XAUUSD currency line itself and `is_gd2_message` requires
XAUUSD in the trigger, so nothing that reaches those three lines can fail
them. The only input that would is self-contradictory. That is a true
survivor, not a missing test, and the source says so at the line. The guard
stays because the live path has it and this function's entire job is to not
diverge from the live path.

A first attempt at a currency test used a EURUSD message the parser could not
read in any currency, so it passed with the guard deleted — a test that
proved nothing. It was replaced with a real Gold Diggers VIP layout plus its
XAUUSD twin, which at least pins the behaviour even though the parsers, not
the guard, deliver it.

## What you will still see in the log

The warning does not go away. Every hourly pass re-reads the same window, so
it re-attempts the same bad message and logs one line about it — now naming
the message and saying it carried on, instead of reporting the whole pass as
failed. It stops when the message ages out of the 72h lookback (2026-09-17
15:30). The live scan behaves the same way for the same reason, and the
alternative — remembering which messages failed — is state that would have to
be cleaned up and is not worth it for a line an hour.

`already_present` in the returned dict is still `scanned - recorded`, which
counts chatter and now counts unparseable messages too. It was already a loose
number before this change, it goes to a debug log and has no caller, and
tightening it properly means deciding what the field is actually for. Left
alone, recorded here so it is not mistaken for a fresh defect.
