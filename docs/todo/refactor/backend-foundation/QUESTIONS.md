# Backend Foundation — decisions to confirm

Plain-English choices to settle. Each has a **recommendation** — say "go with the
recommendations" and only change what you disagree with. Answered items stay here, annotated —
they're not deleted, so later sessions can see why a call was made.

Answer inline (write `ANSWER:` under each still-open one).

## The decisions (quick list)
1. ~~Which repo?~~ **ANSWERED**
2. ~~ORM or repo/adapter pattern?~~ **ANSWERED**
3. ~~Which engine first?~~ **ANSWERED**
4. ~~How much scope in this first pack?~~ **ANSWERED**
5. ~~Which tasks need your sign-off?~~ **ANSWERED**
6. Database consolidation across the 4 engines — one DB or keep separate?
7. Is the NiceGUI UI layer in scope for a future pack, or backend-only forever?
8. What proves an engine's migration is "done" and safe to cut over live?
9. Does the KeyGen licensing/distribution angle change how this should be built?
10. Money stored as float in `gd_copy_signal` — fix now or later?

---

## 1. Which repo? — ANSWERED (2026-07-19)
**ANSWER:** `forex-refactor2`. The earlier `forex-refactor` fork (Phase 0 only, no real code
written) is abandoned/dormant.

## 2. ORM or repo/adapter pattern? — ANSWERED (2026-07-19)
**ANSWER:** Repo/adapter pattern — parameterized SQL behind a typed interface with a
transaction wrapper, per `database-conventions`. Not a traditional object-relational ORM.

## 3. Which engine first? — ANSWERED (2026-07-19)
**ANSWER:** `gd_copy_signal` — smallest engine (1,295-line `engine.py`).

## 4. How much scope in this first pack? — ANSWERED (2026-07-19)
**ANSWER:** `gd_copy_signal` only — DB layer + service extraction. Not the shared `src/`
skeleton or v1 API directory app-wide; those wait until this proves out.

## 5. Which tasks need your sign-off? — ANSWERED (2026-07-19)
**ANSWER:** Only tasks touching a live/demo MT5 order path (task 050). 010–040 proceed under
TDD without per-task pauses.

---

## 6. Database consolidation across the 4 engines?
Right now there are 5+ separate SQLite files (`vantage.db`, `test_signal.db`,
`gd_copy_signal.db`, `breakout_signal.db`, `forex_trader_demo.db`). This pack doesn't touch
that question — it only affects `gd_copy_signal`'s own DB — but the answer shapes how 010's
adapter foundation should be designed (single shared connection pool vs one per engine).

- **Keep separate per-engine DBs for now (Recommended)** — lower risk, matches the current
  architecture, this pack's adapter still works fine either way. Revisit once 2-3 engines are
  migrated and the pattern is proven.
- **Design for eventual consolidation from the start** — more upfront design work in 010, pays
  off later if consolidation is likely.

ANSWER:

## 7. Is the NiceGUI UI layer in scope for a future pack?
Several `ui/pages/*.py` files also exceed 800 lines (`settings.py` at 3,128, `trading.py` at
2,879). This pack leaves them untouched.

- **Backend-only for the foreseeable future (Recommended)** — the UI keeps calling into
  whatever the backend exposes; a UI-restructuring pack would be considered separately, later,
  if it's still worth it once the backend is done.
- **Plan for a UI pack too** — worth scoping now so future backend interfaces are designed with
  the eventual UI split in mind.

ANSWER:

## 8. What proves an engine's migration is "done" and safe to cut over live?
This pack's own task-level Acceptance criteria (020's characterization suite passing, 050's
demo validation) prove *this engine* is solid. There's no app-wide cutover criteria yet for
switching the live app itself from `forex` to `forex-refactor2`.

- **Decide this later, once 2+ engines are migrated and the pattern is proven (Recommended)** —
  premature to design a cutover checklist before knowing what the finished shape looks like.
- **Define it now** — e.g. N days of parallel demo-account operation with matching output, a
  fixed test suite, your manual sign-off per engine.

ANSWER:

## 9. Does the KeyGen licensing/distribution angle change how this should be built?
The separate KeyGen codebase suggests this app might eventually go to other users, not just
you.

- **Not a factor for this pack (Recommended)** — `gd_copy_signal`'s structure doesn't change
  based on single- vs multi-tenant use; revisit if/when distribution plans firm up.
- **Design with multi-tenant config isolation in mind now** — more upfront complexity in 010's
  adapter (e.g. per-tenant DB paths) for a use case that may not materialize.

ANSWER:

## 10. Money stored as float in gd_copy_signal — fix now or later?
`pnl_dollars`, `net_pnl_dollars`, `balance_after` etc. are SQLite `REAL` columns — a real
defect per `database-conventions` §6 (floats don't round-trip money exactly). Fixing it means
changing the schema and every consumer that reads those columns: the UI panel, the sync
protocol, Telegram alerts — all outside this pack's scope.

- **Defer to its own later pack (Recommended)** — this pack stays focused on structure +
  transactions, not a money-representation migration that ripples app-wide.
- **Fix it now, inside this pack** — bigger scope, but avoids migrating the schema twice (once
  for structure, once for money type).

ANSWER:

---

## Quick-confirm checklist
- [x] 1 — forex-refactor2
- [x] 2 — repo/adapter pattern
- [x] 3 — gd_copy_signal
- [x] 4 — gd_copy_signal only, this pack
- [x] 5 — only 050 needs sign-off
- [ ] 6 — DB consolidation: in / which option?
- [ ] 7 — UI scope: in / which option?
- [ ] 8 — cutover criteria: in / which option?
- [ ] 9 — multi-tenant: in / which option?
- [ ] 10 — money-as-float: in / which option?
