# Review remediation — phase 3: pay down the expansion tax

**Status:** not started
**Gated on:** phase 2 task 010 landed and honestly green (the gates must be real before the cleanup
they police) — 030/040/050 may start earlier if capacity allows
**Touches money:** no (task 030 delegates to a pack that contains one money task, governed there)

## Goal of this phase

At the end of this phase, the structural debt that makes every new feature more expensive is gone:
no dead code, one copy of each shared engine building block, `database.py` and the giant frontend
pages split to house rules, and the money path held to explicit coverage floors.

## Docs

| Doc | Contents | Money |
|---|---|---|
| [010-delete-dead-code.md](010-delete-dead-code.md) | Remove ~2,800 dead lines; drain the orphan-gate baseline to empty | no |
| [020-consolidate-engine-shared-code.md](020-consolidate-engine-shared-code.md) | One home for indicators/level detection; break service import cycles | no |
| [030-execute-frontend-restructure-pack.md](030-execute-frontend-restructure-pack.md) | Unblock + sequence the existing docs/todo/refactor/frontend/restructure pack | no* |
| [040-split-database-py.md](040-split-database-py.md) | Split schema/migrations; retire the 100-name re-export hub | no |
| [050-frontend-exception-timer-hygiene.md](050-frontend-exception-timer-hygiene.md) | Kill the 31 silent excepts + 33 sync polls; monkey-patch canary | no |
| [060-money-path-coverage-floors.md](060-money-path-coverage-floors.md) | Broker/runtime floors; tests for mt5_native + manual limit orders | no |

## Exit criteria

- Orphan-gate baseline file deleted (empty debt ledger); gates green on the slimmed tree.
- No cross-engine imports of another engine's internals; cycle count at zero for the named pairs.
- 001-frontend-restructure pack shows real progress per its own PROGRESS.md.
- `python -m tools.checks all` fully green throughout — every deletion proved by the suite.
