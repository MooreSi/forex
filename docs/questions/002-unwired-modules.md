# Q002 — Four built-but-unwired modules: wire, keep, or remove?

**Decision:** PROVISIONAL — leave all four as recorded debt (in the orphan-module
allowlist); delete none; keep the backtest harness as a tool. Awaiting decisions.
**Who decides:** the brother for `rule_generator` and `licence/client` (feature/
business/security); Darren can call `backtest` and `test_signal/auth`.
**Consumed by:** review-august-08 phase3/010 (dead-code deletion).
**Evidence:** `tools/refactor_audit/orphan_module_allowlist.json` +
[phase3/010 task notes](../todo/review-august-08/phase3-expansion-tax/010-delete-dead-code.md).

## The situation

The new orphan-module gate found 7 modules that nothing imports. Three are
genuinely dead duplicates (the per-engine `database.py` clones — superseded by
their `*_repo.py`; they'll be deleted deliberately because tests still touch
them). The **other four are not dead — they were built and never wired in.**
Deleting an intended feature is destructive and hides the wiring bug, so nothing
was deleted. Each needs a call:

| Module | LOC | What it is | Options | My lean |
|---|---|---|---|---|
| `channels/rule_generator.py` | 275 | Auto deterministic-rule generation from an approved AI-recovered signal — a feature the user "explicitly chose" | (a) wire it in; (b) it's superseded by `ai_rule_generator.py` → remove; (c) leave | **Verify first** — the codebase references a differently-named `ai_rule_generator.py`; find which is live before deciding |
| `breakout_signal/backtest.py` | 226 | Walk-forward harness to validate breakout recalibrations *before* they touch live trading | (a) keep as a manual dev tool; (b) wire to a UI; (c) remove | **Keep (a)** — a pre-live safety tool is worth having even if run by hand |
| `config/licence/client.py` | 90 | Licence client: HTTP to the auth server, cert pinning | (a) wire in; (b) remove; (c) leave until the licence rework (phase4/030) | **Leave (c)** — decide alongside the licence rework, not in isolation |
| `test_signal/auth.py` | 51 | Password protection for the TEST module | (a) wire back; (b) remove | Need to know: was TEST-module auth intentionally dropped? |

## The question for each

Wire it in (it's a bug that it's disconnected), keep it (it's a tool / dormant
infra we want), or remove it (obsolete)? Write your answer per row.

**Decision (per module):**
- `channels/rule_generator.py`:
- `breakout_signal/backtest.py`:
- `config/licence/client.py`:
- `test_signal/auth.py`:

Until answered, the gate keeps all four as recorded debt (green), so the queue
does not block other work.
