# Open questions from the autonomous refactor run

Written during the run that finished M4/M5/M7 and the small items. Nothing
here blocked the work — each item was resolved with a stated assumption, or
is genuinely a human-only action. Answers can be applied afterwards.

Ordered by how much they matter.

---

## 1. M6 (close-path re-extraction) was NOT done — it needs your brother

**Status: deliberately not attempted. This is the one milestone left.**

M6 re-extracts the CloseTradeContext cluster — the five modules deleted in
the Phase 0 audit because their extractions were built on a broken partial
context. It **rewrites order-closing code**.

The standing safety rule for this whole project is: *no real or demo MT5
order is ever placed, closed or modified by this work or its tests*, and
any reshaping of the close path waits for (a) explicit sign-off and (b) a
session against a **demo** MT5 account watching trades open and close
correctly.

I cannot perform (b) — it requires a human at a live demo terminal. So the
close path has been left byte-identical throughout every batch of this run:
`_make_close_trade_ctx`, `close_trade` and `record_close` were renamed at
most, never reshaped. `test_close_trade_characterization.py` passes
unmodified as the witness.

**What you need to do:** sit with a demo account, then M6 is roughly one
session of work.

---

## 2. `mt5_bridge.py` (1,335 lines) — split or permanently exempt?

It sits at the repo root deliberately, because it runs as a subprocess
under a *different Python interpreter* (the Wine/Windows one with the MT5
package). It is the largest remaining file over the 800-line ceiling.

**Assumption used:** left alone, exempt in practice. Splitting a file that
executes under a separate interpreter risks import-path breakage that the
test suite here cannot catch, and the ceiling is a code-health heuristic,
not a correctness rule.

**Decision needed:** grant it a written permanent exemption in the LOC
gate, or schedule a careful in-place split with a Wine-side smoke test.

---

## 3. Expert Tunables (M7) — three decisions, all reversible

M7 is built and live at **Settings → Expert Tunables**. Defaults are
byte-identical to the previously hardcoded constants, so *nothing trades
differently until you move a dial*. Three things want your eye:

**3a. The Tier-A list.** I shipped the values CONFIG_AUDIT.md identified as
genuinely trader-facing. If any of them should not be user-editable, say
which and they come out.

**3b. Safe min/max ranges.** Every parameter has a clamp. I chose ranges
that bracket the current default without allowing obviously destructive
values. These are guesses informed by the code, not by trading experience
— worth a review, especially anything that gates order placement.

**3c. Hardcoded Telegram group IDs.** These are still constants, not
channel config. Promoting them is a schema change to the channel table;
I left it alone as out of scope for a tunables page.

Because several of these values gate order placement, the page should get
a pass in the M6 demo session.

---

## 4. Money is stored as floats (carried over from QUESTIONS.md Q7 #10)

Balances, P&L and prices are Python floats throughout. Float arithmetic
loses cents at the edges and the errors accumulate over many trades.

**Not changed here** — it touches trading maths, which is exactly what the
demo gate exists to protect. It wants deciding *before* M6 rewrites the
close path, since that is the natural moment to introduce Decimal.

---

## 5. Q3 — eyeball the new Telegram trade sizes

Still open from the original audit. The Telegram lot-sizing fork was fixed
earlier in this project (Max Risk per trade % now applies on every entry
path, where before Telegram entries bypassed it). That means Telegram
trade sizes **changed**. Nobody has yet confirmed the new sizes look right
against a real account's risk appetite.

---

## 6. Smaller things I decided rather than asked

- **`SimulationEngine` → `TradingRuntime` rename.** Done as its own
  mechanical commit, as planned. The class is a runtime, not a simulator;
  the old name predates it doing real broker work.
- **Facade method-count baseline was raised twice**, for `_make_scan_ctx`
  and the other ctx builders. Each is one new method against hundreds of
  lines removed. Called out in the commits rather than done silently.
- **Test-fixture migration** (119 local `fresh_db` copies → the canonical
  one in `tests/conftest.py`) was done opportunistically on files this run
  touched, not exhaustively. The rest is safe, mechanical, and can happen
  whenever.
