# 057 — Four definitions of "the Asian session", disagreeing on eight hours of the day

**Status:** found 2026-09-12. **Not fixed** — reconciling them changes which
hours trading is allowed in and re-labels historical P&L. Both are the owner's.
**Touches money:** yes. One of the four decides whether an order may be placed
at all; another decides which session every trade's P&L is attributed to.
**Severity:** every conversation about "the Asian session" in this app —
including the open one in `docs/simon-handover/033` — is about a window whose
boundaries depend on which file is asking.

## The four

| | file | Asian is |
|---|---|---|
| 1 | `reversal_engine/level_detector.get_session` | 00:00–07:59 |
| 2 | `test_signal/signal_generator.get_session` | 23:00–07:59 |
| 3 | `channels/strategy_ai` (`_ASIAN_END_UTC = 7`) | 00:00–06:59 *(decorative — see below)* |
| 4 | `dpm.engine.detect_session` = `analytics/read_repo._session_for_hour` | 21:00–06:59 |

Hour by hour, UTC:

| h | reversal | bounce | dpm / analytics | strategy_ai |
|---|---|---|---|---|
| 00–06 | asian | asian | asian | asian |
| **07** | **asian** | **asian** | **london** | **london** |
| 08–11 | london | london | london | london |
| 12–15 | overlap | overlap | overlap | overlap |
| **16** | **overlap** | **overlap** | **ny** | — |
| 17–20 | ny | ny | ny | — |
| **21–22** | **off** | **off** | **asian** | — |
| **23** | **off** | **asian** | **asian** | — |

Eight of twenty-four hours disagree.

## Why it matters, specifically

**1. The Trading Markets buttons use definition 4.** `is_session_allowed` — the
gate that refuses an order outside the enabled sessions — calls
`dpm.detect_session`. So the **Asia** button covers 21:00–06:59: two hours both
engines call "off", and *not* 07:00, which both engines call Asian.

**2. Every per-session P&L figure uses definition 4.** The channel scorecard's
`sessions` split comes from `analytics._session_for_hour`. A trade the Reversal
Engine opened at 07:30 as an Asian-session trade is reported to the owner as a
London one.

**3. The new Asian exemption uses definition 1.** `capability_gates.asian_bias_exempt`
compares against `level_detector.get_session`, so when it is switched on it
will stand the trend gate down for 07:00 — an hour the app's own trading-hours
logic calls London, and the hour immediately before the London open.

**4. `strategy_ai` has no session at all after 16:00.** Definition 3 handles
only `hour < 7`, `7–11` and `12–15`; every hour from 16:00 falls through to the
`conservative` default. That may be intended — it is a regime classifier, not a
session map — but it means "conservative after 16:00 UTC" is a rule nobody
wrote down, hidden in the shape of an if-chain.

**5. Definition 3 is decorative.** Found by mutation-testing it: deleting the
`hour < _ASIAN_END_UTC: return "conservative"` branch changes no answer at all,
because every hour it covers (00:00–06:59) matches neither the London branch
(7–11) nor the overlap branch (12–15), and so reaches the same `conservative`
default anyway. The line states an intention the code does not depend on.

So the honest count is **three definitions that act and one that does not** —
which does not make the disagreement smaller, because the three that act are
the three that matter: the engines, the trading-hours gate, and the P&L
attribution.

## What it does not mean

None of this is wrong arithmetic, and no trade has been mispriced. Each
definition is locally sensible and three of the four agree for sixteen hours a
day. The cost is that a decision taken about "Asia" in one place does not land
where a reader expects, and a measurement of "Asia" in another place is not the
same population.

That is precisely the situation `docs/simon-handover/033` is in: the Reversal
Engine's Asian numbers were measured on definition 1, the Bounce engine's on
definition 2, and the P&L attribution the owner reads on the History page uses
definition 4.

## What it would take

One definition, in one module, imported by the other three — with the boundary
hours decided deliberately rather than inherited. The decisions are:

* **Does 07:00 belong to Asia or London?** The engines say Asia, the gate says
  London. Moving it moves an hour of signals across the exemption boundary.
* **Are 21:00–22:59 Asian or nothing?** The gate says Asian, so today the Asia
  button controls them; the engines ignore them entirely.
* **Is 16:00 overlap or NY?** Cosmetic for trading, not for attribution.

Every one of those changes which hours are tradeable or re-labels history, so
this is a sitting with the owner and not an overnight tidy-up. It is also worth
doing before anyone acts on a session-split measurement again.
