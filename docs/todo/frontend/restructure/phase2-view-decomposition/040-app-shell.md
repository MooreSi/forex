# 040 — Split the app shell `app.py` (1,633 lines)

**Status:** not started — **blocked on [QUESTIONS.md](../QUESTIONS.md) Q1**
**Depends on:** 2/010 (the convention); Q1 answered
**Touches money:** no. But `app.py` holds the Local/Remote mode toggle, and switching modes decides **which node places trades**. Moving that code is not money-touching; getting it wrong is. Treat the mode toggle with the care of a money task even though the paperwork does not require it.
**Layer:** frontend
**Leverage:** `/split-file`; phase-1 tasks 010, 020 and 040 already rewired this file's service imports

## Problem

`frontend/app.py` is **1,633 lines** and baselined. It is genuinely several things at once:

| Contents | Roughly | Nature |
|---|---|---|
| NiceGUI timer + WebSocket buffer patches | `:14-60` | framework workarounds, must run at import |
| Startup/shutdown hooks | `:165-173` | composition |
| `_render_about()` — About, Setup Instructions, Version History, Glossary | `:177-706` | **pure content data** |
| Power and Pause dialogs | `:744-887` | components |
| Ticker strip — bid/ask, balance, equity, sparkline, badges | `:889-968` | components |
| Local/Remote mode toggle | `:970-1100+` | component with real behaviour |
| Page/tab wiring | rest | composition |

The `_render_about()` block alone is ~530 lines, and almost all of it is literal strings: setup steps,
glossary definitions, orchestration descriptions. That is content living in the application shell.

## Decision

**Blocked pending Q1.** The recommendation on the table is: split what is genuinely a component or
genuinely content, then stop — do not chase a number.

Under that answer:

- `_render_about()`'s content → a data module (`frontend/pages/about/_content.py`) holding the
  glossary, setup steps and orchestration text as data, with a small renderer beside it. This is the
  single biggest and safest win in the file.
- Ticker strip → `components/shell/_ticker.py`
- Power + Pause dialogs → `components/shell/_dialogs.py`
- Mode toggle → `components/shell/_mode_toggle.py`
- Framework patches, startup hooks and page wiring stay in `app.py` as composition.

If Q1 comes back "full split to under 800" or "leave it alone", rewrite this task before starting.

## What must NOT change

- **The framework patches at `:14-60` run at import, before any client connects.** The timer teardown
  patch and `max_http_buffer_size = 10_000_000` are both process-wide and both fix reproduced
  production failures. They stay in `app.py`, at module level, in the same order, executing before
  anything else.
- **The Local/Remote handshake.** `_toggle_mode()` performs a stand-down request that must be
  acknowledged by the VPS *before* this node starts trading, and the sub-engine start/stop that
  follows. Order, timeouts and failure handling are byte-identical. If the acknowledgement path is
  even slightly reordered, both nodes can trade the same account.
- **Function-local imports stay function-local** — `:982`, `:1127`, `:1143`, `:1246`. Each defers a
  heavy import past boot.
- **`@app.on_startup` / `@app.on_shutdown` still call `_lifecycle_startup` / `_lifecycle_shutdown`**,
  unchanged. Headless mode calls the same functions by a different route, and this is the one
  implementation both entry points share.
- **The favicon versioning trick** (`_FAVICON_VERSION` from the startup timestamp) — it exists
  because Safari caches favicons by URL in its own database.
- The audio unlock script and the cash-register synthesis: same JS, injected at the same point in
  page load. The unlock must still precede any timer-driven playback.
- Every string in the About / Glossary / Setup content is preserved **exactly** — this is user-facing
  documentation, and a "tidied" sentence is a changed document.
- `ui.run()` parameters in `run.py:262-277` are untouched by this task.

## Tests first (TDD)

- `tests/frontend/test_app_shell_patches.py::test_the_framework_patches_are_applied_at_import`
  — structural. Asserts `max_http_buffer_size == 10_000_000` and the timer methods are the patched
  ones, after importing `frontend.app`.
- `tests/frontend/test_app_shell_patches.py::test_the_patch_check_notices_an_unpatched_timer`
  — **negative control**.
- `tests/frontend/test_about_content.py::test_every_glossary_and_setup_string_is_preserved`
  — characterization, written **before** the move: hash or enumerate every string in
  `_render_about()` and assert the same set after.
- `tests/frontend/test_about_content.py::test_the_string_check_notices_an_edited_sentence`
  — **negative control**.
- `tests/frontend/test_mode_toggle_wiring.py::test_take_over_waits_for_the_stand_down_ack`
  — wiring, with a fake sync controller. Asserts no engine starts before the acknowledgement returns.
- `tests/frontend/test_mode_toggle_wiring.py::test_the_test_would_catch_an_early_start`
  — **negative control.** The failure this guards against is two nodes trading one account; an
  assertion that cannot see an early start is worth nothing here.
- `tests/frontend/` boot smoke — app boots and serves; **headless mode boots** too.

## What to do

1. Get Q1 answered. Do not start without it.
2. Write the tests; run them; confirm they fail for the right reason.
3. Read `/split-file`.
4. Move the About content first — biggest, safest, pure data.
5. Then dialogs, then the ticker.
6. **Mode toggle last, on its own commit**, with the handshake tests green before and after.
7. Verify headless mode boots: it shares `startup()`/`shutdown()` with this file.
8. `python -m tools.checks all`.

## Where

- `frontend/app.py` — reduced to patches, hooks and composition
- `frontend/pages/about/` — content + renderer
- `frontend/components/shell/` — `_ticker.py`, `_dialogs.py`, `_mode_toggle.py`

## Acceptance

- `app.py` contains framework patches, lifecycle hooks and composition — and a reader can tell that
  at a glance.
- Every About/Glossary/Setup string byte-identical.
- **The killer test:** with a paired VPS, toggle Local → Remote → Local. The stand-down is
  acknowledged before this node starts trading, all three sub-engines stop and restart correctly, and
  at no point are both nodes able to place an order. Then confirm headless mode still boots.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- If a paired VPS isn't available for the killer test, do everything else, leave this
  `blocked — mode toggle unverified` in PROGRESS.md, and say so. Do not mark it Done on the
  fake-based tests alone: they prove the ordering, not the integration.
- `runtime.py` stopping at 1,310 lines is the precedent for a composition root having a floor. If
  `app.py` lands at 500 and will not go lower without inventing modules, that is the answer — record
  it in the phase-3 docs task as a deliberate exemption with the reason, the way M4 did.
