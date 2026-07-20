# Core Scan Messages Migration — Scoping

`SimulationEngine._scan_messages` (core/engine.py:6252-7388, 1,137 lines)
is the final, largest, and highest-risk piece of the entire
`core/engine.py` migration: the per-cycle Telegram signal-parsing state
machine that drives every automatic trade this app places from a channel
message. It is comparable in density to the DPM handler + AI fallback +
IME clusters combined, all inside one method — read in full on 2026-07-20
before scoping (four `Read` passes, 6252→7388).

Unlike every prior pack in this migration series, this one needs its own
multi-pack breakdown rather than a single 010/020 characterize/extract
pair — the same reasoning `core-mt5-history-migration`'s README used for
bundling three related methods, scaled up for a single method with this
much internal structure. Each sub-pack below gets its own
`docs/todo/refactor/core-scan-messages-<slice>-migration/` directory,
following the exact same throwaway-trace-first / characterize-then-extract
/ full-suite-then-live-app-verify rigor as every other pack in this series.

## Already-extracted collaborators this method calls (reuse, don't re-derive)

Confirmed by direct inspection before scoping — every sub-pack below
should mock/fake these rather than re-testing their own internals, which
are already covered in their own packs:

| Collaborator | Extracted in | Module |
|---|---|---|
| `_try_ai_signal_fallback` | `core-ai-signal-fallback-migration` | `core_ai_signal_fallback.try_ai_signal_fallback` |
| `_apply_sl_adjustment` | `core-ai-signal-fallback-migration` | `core_ai_signal_fallback.apply_sl_adjustment` |
| `_queue_unrecognised` | `core-ai-signal-fallback-migration` | `core_ai_signal_fallback.queue_unrecognised` |
| `_process_instant_entry` | `core-instant-entry-migration` | `core_instant_entry.process_instant_entry` |
| `_find_and_apply_instant_followup` | `core-instant-followup-migration` | `core_instant_followup.find_and_apply_instant_followup` |
| `open_trade` | `core-open-trade-migration` | `core_open_trade.open_trade` |
| `close_trade` | `core-close-trade-migration` | `core_close_trade.close_trade` |

## Not extracted, taken as unextracted `self.X` collaborators (out of scope here)

Small pure/near-pure helpers with no branching complexity of their own,
called by the auto-execution sub-pack but not worth a dedicated pack:
`_check_pre_trade_filters`, `_price_in_entry_range`, `suggest_lot_size`,
`_get_trading_balance`. Faked/mocked wherever the flow calls them, same as
`self.pnl`/`self.get_open_trades` were treated as pass-through elsewhere in
this series.

## Sub-pack breakdown

| # | Slice | Lines (approx) | Real-money surface | Status |
|---|---|---|---|---|
| A | `core-scan-messages-edit-reparse-migration` | 6330-6561 (~230) | Can flatten (close) an open position via `close_trade` when an instant-entry edit flips direction | Pending |
| B | `core-scan-messages-parse-classify-migration` | 6601-6807 (~200) | None — parsing/classification + DB recording only | Pending |
| C | `core-scan-messages-staleness-strategy-migration` | 6809-6982 (~175) | None — staleness recording + per-channel strategy resolution (incl. AI evaluation) | Pending |
| D | `core-scan-messages-auto-execute-migration` | 6984-7364 (~380) | **Highest** — places a real MT5 order via `open_trade`, gap-adjusts entry levels, applies Conservative/Scalp Runner post-fill SL/TP overrides via `modify_order`/EA `update_trade` | Pending |
| E | Thin glue (preamble, IME/SL-adjustment dispatch gates, final alert) | ~6252-6329, 6563-6599, 7366-7388 | None | Not extracted — permanent thin layer, same judgment as `_handle_bot_command`/`_monitor_loop`'s own dispatch shell |

Sub-packs A-D are independently characterizable: each can be driven by
calling the real `_scan_messages` with a single synthetic Telegram message
+ DB state engineered to land in that slice, with every OTHER slice's own
behavior neutralized (e.g. for slice A, insert an already-existing
`vantage_tg_signals` row so the dedup/edit branch fires immediately;
downstream slices B-D never execute for that message). This mirrors the
"drive the whole method for one iteration, fake everything but the target
block" technique already used successfully for `core-monitor-loop-migration`.

Recommended execution order: A → B → C → D, ascending real-money risk, so
the highest-stakes slice (auto-execution) benefits from every lesson learned
characterizing the lower-risk slices first (exact DB row shapes, dedup/edit
row insertion helpers, staleness-timestamp mocking, etc. — all reusable
scaffolding).

See each sub-pack's own `README.md`/`PROGRESS.md` for detailed status once
started.
