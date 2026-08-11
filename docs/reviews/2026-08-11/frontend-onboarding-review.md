# Frontend & onboarding review — 2026-08-11

Read-only inspection of `frontend/` focused on **onboarding/usability** (the new priority) and the
state of the 001 restructure. No app was run; no code changed. One gate was executed:
`python -m tools.refactor_audit.import_contracts --check`. Context read: the 2026-08-08 frontend
review, the restructure pack at `docs/todo/frontend/restructure/` (PROGRESS.md, README.md,
QUESTIONS.md), `CLAUDE.md`, `docs/system/rules/`, and the new `frontend/auth_gate.py`.

## Summary

The owner's report — *"it's almost impossible for me to know what I'm meant to do"* — is a **real,
reproducible gap, not a knowledge problem**. The app has a lot of good explanatory content, but it
is architecturally invisible to a first-time user:

- The app **lands on the Chart tab** (`app.py:1613`, `value=tab_chart`) — a bare price chart with
  no context, not a "start here" surface.
- There is **no first-run flow of any kind**. A grep for `first_run|has_seen|welcome_shown|onboard|
  intro_dialog` across `frontend/` and `backend/src/` returns **nothing** (the only hits are the
  `onboarding@resend.dev` email sender). Nothing greets a new user, nothing tracks whether they've
  been set up, nothing walks them through the one-time steps.
- The **10 top-level tabs are named in jargon** a non-expert cannot map to intent: `AI Analysis`,
  `Chart`, `Trading`, **`Parsing`**, **`Signal Generator`**, **`Edge`**, `Backtest`, **`Analysis`**,
  `Settings`, `About` (`app.py:1507-1516`). "Parsing" is the Telegram reader; "Signal Generator" is
  the test/engine panel; "Analysis" is trade history; "Edge" is a message-trace dashboard. The label
  gives no hint of the job.
- The genuinely good onboarding material — Bot Orchestration, a full Windows/Mac/VPS **Setup
  Instructions** set, a 6-step Registration guide, and a large plain-English **Glossary** — is all
  **buried inside the last tab (`About`)** and reachable only by clicking one of four nav cards
  (`app.py:228-258`, section bodies `app.py:268-700`). Nothing points a new user there, and its
  content is *installation*-oriented ("how to install MT5 / Telegram / Resend"), not *"the app is
  running — what do I actually do now, day to day."*
- There is **no Help button** anywhere in the header (grep for `help|question_mark|quiz` in
  `app.py` finds only a code comment). The header carries pause/power/admin controls
  (`app.py:1084,1092,1101`) but no route to the guidance that already exists.

Meanwhile, effort has gone into *delight* rather than *comprehension*: a multi-stage **confetti
celebration** fires when you open the History/Analysis tab on a profitable day (`app.py:1565-1605`).
That energy is exactly what the onboarding layer needs and isn't getting.

On structure, the 001 restructure has **not moved**: the controller-boundary contract still reads
**59 violations, baselined** (verified today), `components/` is still an empty `__init__.py`, every
PROGRESS.md row is `not started` (0 of 13 tasks), and the oversized files are byte-for-byte the same
size. Two things changed since 2026-08-08: a login gate was added (`frontend/auth_gate.py`, good and
clean), and the silent-except count **regressed** (31 → 44 `except Exception: pass`).

## Onboarding / usability gap — the priority

### What exists (and is good, but mis-placed)

| Asset | Where | Problem |
|---|---|---|
| Setup Instructions (Win/Mac/VPS, step-by-step) | `app.py:360-591` | Buried in About; install-focused, not day-to-day |
| Registration & Setup (6 numbered steps) | `app.py:345-358` | Buried in About; not linked from anywhere on first run |
| Bot Orchestration guide (10 feature explainers) | `app.py:273-343` | Buried in About; encyclopedic, not a "do this next" path |
| Glossary (40+ terms, plain English) | `app.py:621-700` | Buried in About; not reachable in-context from the tab that uses the term |
| Per-panel empty states ("Click Research Now", "No signals yet") | `ai_summary.py:74`, `backtest.py:355`, `telegram.py:194`, etc. | Tell you a button exists — not *why*, *whether you should press it*, or *what has to be true first* |
| Rich tooltips on individual controls | throughout | Discoverable only on hover; give no top-level orientation |

### What is missing (why a non-expert is stuck)

1. **No orientation on landing.** You arrive on a candlestick chart. Nothing says "the app is
   running; here is what to check and what to do first."
2. **No setup-status feedback.** The app already computes connection/EA status
   (`conn_badge` `app.py:1228`, `ea_badge` `app.py:1249`) and circuit-breaker state
   (`app.py:1533`), and the licence/registration state is known. Nothing aggregates these into a
   single "are you ready to trade?" checklist. Simon cannot tell whether he's finished setting up.
3. **No day-to-day loop described.** The Orchestration guide explains *features* in isolation; there
   is no "your normal routine is: 1) confirm MT5 connected, 2) review pending signals in Trading,
   3) watch active trades" narrative.
4. **Labels don't teach.** Four of ten tab names are opaque. There are no one-line subtitles under
   the tab headers, so the tab bar is a wall of unexplained nouns.
5. **Glossary is not in-context.** Terms like R:R, ADX, DPM, Anchor, Trail appear live on panels,
   but the plain-English definitions sit three clicks away in another tab.

### Concrete proposal — a minimal, high-impact guidance layer

Five changes, roughly in priority order. None of them touches money paths, services, or the close
path; all are view-layer additions.

**1. A first-run "Start Here" checklist (highest impact, ~half a day).**
On load, if `app.storage.user.get("setup_seen")` is falsy, route to (or pop) a **Getting Started**
panel instead of the chart. It shows a live checklist driven entirely by data the app already has:

- ✅/❌ **Licence active** (registration state)
- ✅/❌ **MT5 connected** (reuse `conn_badge` source, `app.py:1228`)
- ✅/❌ **Algo Trading enabled in MT5** (already surfaced in Settings diagnostics)
- ✅/❌ **Risk per trade set** (config)
- ⚪ **Telegram reader connected** (optional — mark clearly optional)
- ✅/❌ **You are in DEMO mode** (env toggle, `app.py:1503`) — reassure before any live step

Each row: a green tick when satisfied, a red cross plus a **"Fix this →" button that jumps to the
exact Settings section**. A "Don't show automatically" checkbox sets `setup_seen`. This converts the
scattered setup docs into a single actionable surface and directly answers "what do I do?".

**2. A persistent Help "?" button in the header** (`app.py` header row, near the pause/power/admin
buttons ~`app.py:1084-1101`) that opens the Getting Started panel / About. One obvious, always-there
route back to guidance. ~1 hour.

**3. One-line subtitles (or plainer names) on the jargon tabs.** Either rename or add a small caption
line at the top of each panel: `Parsing → "Telegram signal reader"`, `Signal Generator →
"Strategy engines (demo)"`, `Edge → "Live message trace"`, `Analysis → "Trade history & stats"`.
Cheapest single change that reduces bewilderment. ~1-2 hours.

**4. Reframe About-home into "Setup once / Every day".** Keep the existing four cards under a
**"Set up (one time)"** heading; add a **"Your daily routine"** card with the 3-step loop above.
Turns an encyclopedia into a path. ~2 hours (content only; the card scaffold already exists at
`app.py:230-258`).

**5. Upgrade the two most-important empty states into next-step prompts.** On **Trading** and
**Analysis** with zero signals/trades, replace the terse "No signals yet" with two lines plus a
button: *"No signals yet. Signals arrive from Telegram channels (set up under Parsing) — or build
one yourself here →"*. Teaches the causal chain at the moment the user is looking for it.

Items 2, 3 and 5 are each an hour or two and would meaningfully move the needle even before item 1
ships. Item 1 is the centrepiece.

## Frontend structure state

**001 restructure: still 0 of 13 tasks, unchanged since the 2026-08-06 scaffold.**

| Metric | 2026-08-08 | 2026-08-11 (today) | Evidence |
|---|---|---|---|
| `frontend-reaches-the-backend-through-controllers` | 59, baselined | **59, baselined** | `import_contracts --check` |
| DB boundary contract | 0, enforced | 0, enforced (holds) | same gate |
| `components/` populated | empty | **empty** (0-byte `__init__.py`) | `frontend/components/` |
| Tasks done | 0/13 | **0/13** | `PROGRESS.md` all `not started` |
| QUESTIONS.md answered | 0/4 | **0/4** | `PROGRESS.md:22` |
| `settings.py` | 3,112 | **3,112** | `wc -l` |
| `history.py` | 1,416 | **1,416** | `wc -l` |
| `app.py` | 1,633 | **1,633** | `wc -l` |
| Other over-budget | ai_trade_analysis 1,250 · test_panel 1,246 · breakout 919 · chart 839 · reversal 804 | **identical** | `wc -l` |
| `except Exception: pass` (frontend) | 31 | **44** (regressed) | grep |
| total `except Exception` (frontend) | 108 | **143** | grep |
| `ui.timer` loops | 33 | 32 | grep |
| direct `backend.src.{services,app,runtime,config}` imports | ~59 | 58 | grep |
| `app.storage` usage | 0 | **7** (new, via auth gate) | grep |

Additional non-baselined contract debt surfaced by today's run: `no-nicegui-in-the-backend`
(2 violations, baselined) and `utils-and-config-depend-on-nothing-above-them` (3, baselined).

**New since last review — the login gate (`frontend/auth_gate.py`, 67 lines).** Clean and correct:
Starlette middleware redirects unauthenticated requests to `/login`, uses a signed
`app.storage.user` cookie, forwards through `auth_controller` (respects the layer rule), keeps
`/_nicegui`, `/static`, `/favicon` open, and preserves the referrer. It also introduces the app's
**first correct use of `app.storage.user`** — which is exactly the mechanism the onboarding
`setup_seen` flag (proposal item 1) should reuse. One usability caveat: it puts a **credentials wall
in front of an app that is already hard to use**. Simon now needs both a login *and* orientation;
the Getting Started work matters more, not less, because of it.

## Findings by severity

### High

**H1 — No first-run guidance path; the app lands on a context-free chart.** `app.py:1613`
(`value=tab_chart`); no `first_run`/`has_seen`/`onboard` logic anywhere (`grep` empty). This is the
direct cause of the owner's complaint. *Fix: proposal item 1.*

**H2 — Controller boundary unchanged at 59; restructure 0/13.** `import_contracts --check` (today).
The service-signature blast radius the 2026-08-08 review flagged (17 files, money-adjacent order
entry in `trading/_manual_entry.py`, `trading/_strategy_cards.py`) is still wide open. Pack appears
stalled on the owner: **QUESTIONS.md 0/4 answered** (`PROGRESS.md:22,69`).

**H3 — Silent-except regression: 31 → 44 `except Exception: pass` in `frontend/`** (143 total
`except Exception`). In a live-money dashboard these swallow refresh/fetch failures and leave
stale-but-plausible numbers on screen with no log and no indicator. The trend is going the wrong way.

### Medium

**M1 — Ten jargon tab labels with no subtitles** (`app.py:1507-1516`). `Parsing`, `Signal
Generator`, `Edge`, `Analysis` are unguessable. *Fix: proposal item 3.*

**M2 — Rich onboarding content is unreachable in practice.** Setup Instructions (`app.py:360-591`),
Registration (`app.py:345-358`), Orchestration (`app.py:273-343`), Glossary (`app.py:621-700`) all
live behind the last tab's nav cards with nothing linking to them and no header Help button. *Fix:
items 2 and 4.*

**M3 — No aggregated setup/readiness status.** The pieces exist independently (`conn_badge`
`app.py:1228`, `ea_badge` `app.py:1249`, circuit breaker `app.py:1533`, env toggle `app.py:1503`)
but nothing composes them into "are you ready to trade?" *Fix: item 1.*

**M4 — `settings.py` still a 3,112-line monolith embedding process management in the view.** No
change since 2026-08-08 (bridge `subprocess.Popen`, Wine detection, `pgrep`). Relevant to
onboarding because *Settings is where every setup step lands* and it's the least navigable page in
the app for a non-expert.

**M5 — `components/` still empty.** The two things already duplicated across engine panels
(`_fmt_ts`/`_fmt_dur`/`_dir_color`/`_pnl_color`; the `_safe_refresh`+timer tail) have nowhere to
live, so a shared onboarding/empty-state component would also have nowhere to live. Seeding
`components/` should precede any onboarding-widget work so it isn't copy-pasted per page.

### Low

**L1 — Delight before comprehension.** Multi-stage confetti on profitable-day History visits
(`app.py:1565-1605`) while no equivalent effort greets a lost first-time user.

**L2 — Empty states describe controls, not consequences.** e.g. `telegram.py:194`, `backtest.py:355`,
`test_panel.py:429`. Fine individually; collectively they never tell a newcomer what has to be true
before a control does anything. *Fix: item 5 (top two only).*

**L3 — About header says "FOREX Trader by Simon Moore"** (`app.py:189`) — worth confirming the
byline is intended given the app is being handed *to* Simon.

## Prioritized recommendations

1. **Build the first-run "Start Here" checklist (proposal item 1).** Single highest-impact change;
   directly answers the owner's complaint; reuses the just-added `app.storage.user` and existing
   status sources. View-layer only, no money paths.
2. **Ship the three cheap wins now (items 2, 3, 5):** header Help button, tab subtitles/renames, and
   upgraded Trading/Analysis empty states. A few hours total; each independently reduces the "what do
   I do" gap and none needs the restructure to land first.
3. **Reframe About-home into "Set up once / Every day" (item 4)** and add a header link to it, so the
   already-written guidance becomes a path rather than an encyclopedia.
4. **Get the four QUESTIONS.md answers from the owner** to unblock the restructure — it has not moved
   in five days and phase-2 task 040 is blocked on Q1. Onboarding widgets should be built as the
   first residents of `components/` (item M5), not pasted into `app.py`, so seed the component
   convention (phase-2 task 010) alongside.
5. **Stop the silent-except regression (H3):** at minimum `log.debug` + a visible "data stale
   since…" indicator on the refresh pollers; do not let the count climb past 44.
6. **Do not fold onboarding into the money-touching lanes.** All proposed work is view-only; keep it
   clear of `trading/_manual_entry.py` / `_strategy_cards.py` and the frozen close path.
