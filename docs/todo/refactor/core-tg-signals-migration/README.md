# Core: TG Signals Migration

**Status:** planning (pre-implementation)
**Domain:** refactor
**Created:** 2026-07-20

## 👋 Picking this up (agents start here)

Seventh `core/engine.py` domain pack. Read
[core-untracked-positions-migration](../core-untracked-positions-migration/) first — same
"take the collaborator as an explicit parameter instead of `self.x`" pattern applies here.

## What we're building & why

`get_tg_signals` (line 7474) — reads raw parsed Telegram signal history from
`vantage_tg_signals` for the History/audit UI, with a best-effort group-name enrichment via
`self._tg_reader.get_group_name(...)` when a row's `group_name` wasn't captured at parse time.
Pure read, no writes, no MT5 involvement at all.

## Target methods (from `core/engine.py`)

| Current method | Lines | New home |
|---|---|---|
| `get_tg_signals` | 7474-7494 | `core_tg_signals.py` |

Takes `tg_reader` as an explicit optional parameter (anything exposing `get_group_name(group_id:
str) -> Optional[str]`, matching `TelegramReader`'s real shape) instead of reading
`self._tg_reader`.

## Doc index

| Doc | Contents |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Live status log |
| [010-characterize-tg-signals.md](010-characterize-tg-signals.md) | Characterization tests against current `engine.py` |
| [020-extract-tg-signals.md](020-extract-tg-signals.md) | Extract into a standalone, tested function |

## Decisions locked (2026-07-20)

| Decision | Choice | Source |
|---|---|---|
| Scoping strategy | Continuing packs 1-6's precedent: one `core/engine.py` domain per pack, smallest/lowest-risk first | user, 2026-07-20 (established for the whole `core/engine.py` series) |
| This pack's scope | `get_tg_signals` only | this file |
| Real-money surface | None — pure read | verified by reading the code |
| `engine.py` itself | Left untouched — new function exists standalone/tested, not wired in | precedent |

## Out of scope (explicitly, for this pack)

Everything not `get_tg_signals`. This is the last trivially-safe pure-read/pure-bookkeeping
cluster reachable without touching real trade execution, the 13 TP/SL strategy handlers, IME,
bot commands, or background loops — see PROGRESS.md for the state of the wider `core/engine.py`
migration and what's left.
