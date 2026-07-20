# Core Open Trade Migration — PROGRESS

_Last updated: 2026-07-20 — 020 done, pack complete._

## Tasks

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 010 | characterize-open-trade | done | agent, 2026-07-20 | 15 tests, all green. Found and fixed an environment gap: `cryptography` (a declared `requirements.txt` dependency) was missing from the pyenv 3.11.9 venv `python -m pytest` actually uses, silently masking the whole Local/Remote sync-forwarding branch via the existing `except ImportError: pass`. Installed it; no `engine.py` bugs found. |
| 020 | extract-open-trade | done | agent, 2026-07-20 | Created `core_open_trade.py` (305 lines, 1:1 port; `bridge` taken explicitly, `ea_bridge`/sync singletons used directly, no new context class needed). 15 new surface tests. 330/330 green in tests/core/. `engine.py` untouched. No real/demo order ever placed (Python bridge or EA). |

## Blockers / open
None. Pack complete. Remaining in the trade-management cluster: `open_trade_from_signal`
(~500 lines, the largest single method in `core/engine.py` — resolves a raw signal into the
parameters this pack's `open_trade` needs: strategy selection, SL/TP calculation, sizing),
`open_manual_market_order`, and `update_signal` (modifies a live order).
