# 040 — Notifications & Telegram → controllers

**Status:** not started
**Depends on:** none — parallel with 010 and 030
**Touches money:** no. Sending an email or reading a Telegram message places no order. The *parsing* of a signal into a trade does — but `signals.parser` is task 020's, not this one's. Do not reach for it here.
**Layer:** frontend → controller
**Leverage:** `telegram_controller.py` (50 lines) exists; notifications has no controller yet

## Problem

| File | Line | Import |
|---|---|---|
| `frontend/pages/settings.py` | 1238, 1265, 1361, 1697 | `services.notifications.email_service` (all function-local) |
| `frontend/pages/trading/_manual_entry.py` | 353 | `services.notifications.email_service` |
| `frontend/app.py` | 1143 | `services.telegram.alerts as _tg` (function-local) |
| `frontend/pages/history.py` | 18 | `services.telegram.alerts as telegram_alerts` |
| `frontend/pages/telegram.py` | 12 | `services.telegram.keywords as logic_kw` |
| `frontend/pages/telegram.py` | 13 | `services.telegram.reader` (multi-name import) |
| `frontend/app.py` | 1127 | `services.test_signal.news_filter.get_current_event` (function-local) |

Four separate `email_service` imports inside one file is the clearest illustration of what the open
boundary costs: nobody could see the other three, so each site imported for itself.

`app.py:1127` (`news_filter`) sits in `test_signal` but is used by the shell for the NEWS EVENT badge
— it is a notification concern from the page's point of view, so it lands here rather than in 010.

## Decision

- **New `notifications_controller.py`** — email send/test, report scheduling, and the alerts surface.
  Flat forwarding only.
- **Extend `telegram_controller`** — reader authentication and group loading, keyword management,
  and the news-event read for the header badge.

Grouping by the page's concern, not the service directory, is why `news_filter` lands in the Telegram
controller rather than the engines one. Record that in the new controller's docstring so the next
person doesn't "fix" it.

## What must NOT change

- **Email delivery.** Resend and SMTP paths, the test-email button, and the daily/weekly report
  schedule all behave identically. An email that sends today sends after; one that fails today fails
  the same way with the same message.
- **API keys and credentials are never logged and never returned to the page in full.** If a current
  call site masks a key, the controller masks it identically. Do not let a forwarding function widen
  what a page can see.
- The Telegram reader's MTProto session handling and the two listener slots. Reconnect churn is a
  known sensitivity — the reader deliberately keeps running across Local/Remote switches.
- The NEWS EVENT badge's trigger condition and timing.
- Function-local imports at `app.py:1127`, `app.py:1143`, and all four `settings.py` sites stay
  function-local.
- `no-nicegui-in-the-backend` stays at **2**. A new controller must not import NiceGUI — including
  for a notification toast. Toasts stay in the page.

## Tests first (TDD)

- `tests/controllers/test_notifications_controller.py::test_send_test_email_forwards_to_the_service`
  — surface, with a fake email service. **No test may send a real email**; assert the fake was called
  and that no socket was opened, in the style of
  `test_bridge_process_relocation.py::test_no_test_in_this_file_can_spawn_a_process`.
- `tests/controllers/test_notifications_controller.py::test_the_fake_would_notice_a_real_send_attempt`
  — **negative control**.
- `tests/controllers/test_notifications_controller.py::test_no_credential_is_returned_in_full`
  — asserts masking is preserved for every function that touches a key.
- `tests/controllers/test_telegram_controller_reads.py::test_keyword_and_news_reads_forward`
  — surface.
- `tests/frontend/test_settings_email_wiring.py::test_all_four_email_sites_reach_one_controller_function`
  — wiring. The point of this task is that four sites converge; assert they converged.
- `tests/frontend/test_settings_email_wiring.py::test_wiring_detects_a_site_left_behind`
  — **negative control**, and the realistic failure mode: one of four call sites missed.

## What to do

1. Write the tests above; run them; confirm they fail for the right reason.
2. Create `backend/src/controllers/notifications_controller.py` with a docstring saying what it owns
   and why `news_filter` is filed under Telegram rather than here.
3. Extend `telegram_controller.py`.
4. Rewire, one file per commit: `telegram.py`, `history.py:18`, `settings.py` (all four sites in one
   commit — they are the same concern), `_manual_entry.py:353`, then `app.py:1127` and `1143`.
5. Check `import_contracts --check` after each commit.
6. `python -m tools.checks all`.

## Where

- `backend/src/controllers/notifications_controller.py` — **new**
- `backend/src/controllers/telegram_controller.py` — extended
- `frontend/pages/settings.py`, `telegram.py`, `history.py`, `trading/_manual_entry.py`, `frontend/app.py`

## Acceptance

- No frontend file imports `services.notifications` or `services.telegram`.
- All four `settings.py` email sites reach the same controller function.
- `no-nicegui-in-the-backend` still at 2.
- **The killer test:** click "Send Test Email" in Settings and receive it, with the Resend path and
  the SMTP path each tried once — behaviour identical to before, including the failure message when
  the key is wrong.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- `telegram.py:13` is a multi-name `from ... import (` — the contract's AST walker emits two names per
  alias, so this single statement may account for several counted violations. Don't be surprised when
  the count drops by more than the number of lines changed.
- `settings.py` is also a phase-2 split target (3,112 lines). Rewire first, split second.
- Sending a test email during development is fine and expected. Sending one from a **test** is not.
