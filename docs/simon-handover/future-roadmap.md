# Future roadmap — ideas for after the handover

**Status: a menu, not a plan.** Nothing here is started, promised, or needed
for the handover. These are the improvements Darren and the review work
identified as worth considering once the app is safely in Simon's hands,
roughly ordered by value. Each notes what it would cost and what would
trigger doing it.

## Near-term (finishing what's in flight)

1. **Finish the frontend tidy-up.** The remaining oversized screens
   (Settings is the big one at ~3,100 lines) get split into small readable
   pieces, and the last ~50 places where screens reach past the proper
   boundary get rerouted. Pure maintainability — the app behaves
   identically. *(This is stage-2 phase 4's remainder; several sessions of
   careful mechanical work.)*
2. **Turn on the automated checks in the cloud (CI).** The workflow exists;
   it starts running on the first push to GitHub. Then every future change
   gets the full test suite run automatically before it can merge.
3. **Raise the safety-critical test floors.** The broker layer sits at ~58%
   test coverage and the core runtime at ~72% — both now have floors so they
   can't fall, but raising them is real protection for future changes.
4. **Signed licence + signed updates.** The licence check works but the
   signing is symmetric, and the remote-update channel stays off because
   it's unauthenticated. Asymmetric signing and signed updates would let
   both be trusted. *(Security work; needs Simon's involvement as the
   licence holder.)*

## Bigger structural moves (do only with a reason)

5. **SQLAlchemy + Alembic for the database.** Considered and deliberately
   rejected during the handover work: the app uses plain SQLite calls, and
   adopting an ORM just to get standard migration tooling would be a large
   rewrite of the money-adjacent data layer for little user-visible gain.
   The in-house migration registry now does the important parts (ordered,
   versioned, fail-closed, tested against old databases). **Trigger to
   revisit:** if the app ever grows a second database backend, a data model
   that changes often, or a second maintainer who expects standard tooling.
6. **A modern web frontend (Next.js/React).** Proposed and rejected
   2026-08-06 on cost: it adds a Node runtime to a Python-only Windows
   install and means rewriting ~18,000 lines against an HTTP API that
   doesn't exist. The two ideas worth keeping — one narrow backend boundary
   and small reusable components — are being delivered inside the current
   framework instead. **Trigger to revisit:** once the controller boundary
   reaches zero (the exact prerequisite a port needs), and only if the UI's
   limitations actually bite — then it becomes a frontend-only project,
   decidable on evidence.

## Evidence & performance (the interesting part)

7. **Data-science validation of the strategies.** The pieces now exist to do
   this properly offline: a deterministic fake market, scripted scenarios,
   and an end-to-end harness. Build on them: walk-forward backtests of each
   engine's real decision code (not a reimplementation), parameter
   sensitivity sweeps, out-of-sample testing for the ML gates, and honest
   reporting of expectancy/drawdown per strategy and per channel. This is
   the work that answers "does this system actually have an edge?" with
   numbers instead of anecdotes.
8. **Broker-fill realism studies.** The fake bridge fills exactly at the
   quoted price by design. Recording real slippage/rejection statistics from
   live-demo running would let the fills be modelled honestly — and feed the
   sizing maths real costs.
9. **Decimal money arithmetic.** Balances and P&L are floats today (a known,
   documented issue). Moving money maths to exact decimal types is the kind
   of deep, risky change to do deliberately, with the coverage floors raised
   first — not casually.

## How to use this list

Pick at most one structural move at a time, write a spec first, and keep the
golden rules: nothing touches how the app trades without Simon's sign-off
and a demo. Items 1–3 are safe background work; items 5–6 need a genuine
trigger; items 7–8 are where the fun is.
