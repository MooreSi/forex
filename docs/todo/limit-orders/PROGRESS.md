# Limit orders — the keyword decides, not the template — PROGRESS

**Shared status log. Any agent picking up a task updates this file** — claim a row (name + date under
Owner), flip its Status as you go, leave a one-line Note (commit / blocker / decision).

_Last updated: 2026-09-10 — 010, 020, 030 and 040 BUILT and green, owner-signed-off. `tools.checks all` passes (11 checks, 6943 tests). Nothing demoed. The EA redeploy and 050 (the Telegram message) remain._

## Status key
`not started` · `in progress` · `blocked` (say why) · `done` (date + commit)

## Overall
- Routing + template management (010-030): **all three done**; the EA redeploy is outstanding
- Revalidation + alerts (040-050): **040 done**; 050 not started, so a withdrawal is currently visible in the log only
- **Gates:** 010/020/040 signed off by the owner 2026-09-10 · tests-first honoured? yes — every test written and watched fail before its code
- **EA redeploy + recompile outstanding** — the owner's action. EA_VERSION is 1.07 and the chart is on 1.06, so `template_blocked_by_stale_build` refuses EVERY template order until `tools/deploy_ea.sh` is run and MetaEditor compiles (F7).
- **Nothing here has been demoed.** Every task changes what a live order does.

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | [limit keywords beat the template](010-limit-keywords-beat-the-template.md) | done 2026-09-10 | Claude | `is_grid_template` shared by both call sites; not demoed |
| 020 | [the template manages the fill](020-the-template-manages-the-fill.md) | done 2026-09-10 | Claude | new `trading/template_levels.py`; SL/TPs from the resting price; not demoed |
| 030 | [carry the template on a resting order](030-carry-the-template-on-a-resting-order.md) | done 2026-09-10 | Claude | EA_VERSION 1.07; **needs `tools/deploy_ea.sh` + F7 — template orders are refused until then** |
| 040 | [revalidate before the fill](040-revalidate-before-the-fill.md) | done 2026-09-10 | Claude | own tunable, on by default; withdraw and re-arm; not demoed |
| 050 | [announce a discarded limit order](050-announce-a-discarded-limit-order.md) | not started | — | depends on 040 |

## Decisions log
- Keyword decides the entry mechanic, template decides the management (owner, 2026-09-10)
- Grid templates unchanged — already resting (this pack, 2026-09-10)
- Re-check breadth: full parity with the queued path (interview, 2026-09-10)
- Proximity trigger: 10 points from the resting price (interview, 2026-09-10)
- A failed re-check withdraws and re-arms until the original TTL; it does not cancel permanently
  (owner, 2026-09-10 — reversed the same day from the permanent-cancel default)
- Template stop on a resting order is measured from the resting price (owner, 2026-09-10, QUESTIONS 1)
- The widened sweep gets its own tunable, default on (owner, 2026-09-10, QUESTIONS 2)
- Flap alerts: first withdrawal + first re-placement, then quiet (owner, 2026-09-10, QUESTIONS 3)

## Verification log

**2026-09-10, the commit of 010/020/030/040.** Run against the exact tree committed:

```
python -m tools.checks all
  structure gates        ok   (2.5s)
  import contracts       ok   (1.9s)
  runtime facade         ok   (0.0s)
  orphan modules         ok   (1.0s)
  undefined names        ok   (1.1s)
  unawaited coroutines   ok   (1.0s)
  late binding           ok   (0.6s)
  boot smoke             ok   (2.8s)
  doc links              ok   (0.1s)
  test suite             ok   (352.6s)
  coverage ratchet       ok   (0.1s)
All checks passed.

pytest tests/ -q
6943 passed, 7 skipped, 12 warnings in 288.40s
```

Close path, checked explicitly because this work sits in `services/trading`:

```
pytest tests/core/test_close_trade_characterization.py -q   17 passed
git diff --stat tests/core/test_close_trade_characterization.py   (empty)
git diff --stat -- close_trade.py partial_close.py               (empty)
```

`TestItNeverCloses` in `test_resting_revalidation_gates.py` reads the sweep module's own source and
fails if any of the four frozen names appears outside its docstring. It passes, and it carries a
negative control so a search matching nothing cannot look like a search passing.

**No real or demo MT5 order is placed, closed or modified by this work or its tests.** Every test
here uses fakes: `FakeMT5Bridge`, `FakeTelegramReader`, an EA double that records what it was asked
to do, and an `EABridge` subclass that records the wire message instead of sending it.

## Blockers / open
- **Nothing here has been demoed.** 010, 020 and 040 all change what a live order does.
- Until 050 lands, a withdrawal reaches the log and not Telegram.
- The EA redeploy for 030 needs the owner.
- One open question in [QUESTIONS.md](QUESTIONS.md): whether the EA recompile ships on its own or
  with the whole pack (Q4). It affects sequencing, not code.
