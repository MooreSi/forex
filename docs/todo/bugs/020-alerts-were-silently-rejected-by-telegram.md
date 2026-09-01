# 020 — 107 Telegram alerts were rejected, including the ones that matter most

**Status:** found and fixed 2026-09-01, from `vantage_telegram_log`.
**Touches money:** no — but it is how the owner finds out about the things that do.
**Severity:** high. An alert that silently fails is worse than no alert, because
the operator believes he would have been told.

## What was wrong

Reading the alert log turned up **107 failures out of 6,866 sends**, going back
to at least 2026-08-26:

```
09-01 16:38  tp_safety_net    Bad Request: can't parse entities: Can't find end of the entity...
09-01 16:37  ea_bridge_lost   Bad Request: can't parse entities: ...
08-26 14:18  ea_bridge_lost   Bad Request: can't parse entities: ...
08-26 11:51  ea_bridge_lost   Bad Request: can't parse entities: ...
```

Not a random 1.6%. The two alerts failing were **`ea_bridge_lost`** and
**`tp_safety_net`** — the notification that the EA has stopped responding and
management was reclaimed, and the notification that the safety net had to
protect a position the live loop missed. `ea_bridge_lost` is the alert for the
whole of [bugs/013](013-ea-stalls-leave-template-trades-unmanaged.md).

## Why

`parse_mode: "Markdown"` plus an unescaped dynamic value. Telegram Markdown v1
treats `_ * ` [` as delimiters, and a lone one is unbalanced:

```python
f"Ticket {trade.get('mt5_ticket')} ({strategy}) was being managed by ..."
```

`strategy` is `be_runner`, `scalp_runner`, `trail_stop`, `scale_out` — every one
carries exactly one underscore.

The infuriating part: `_md_esc` already existed, and **its own docstring names
this exact failure** ("Unmatched ones (e.g. the underscore in 'manual\\_market')
cause a 400 parse error"). It simply was not called at every site.

## The fix, in two parts

**A delivery guarantee, not another escape.** On a 400 whose body contains
`can't parse entities`, the send is retried once with `parse_mode` removed. The
next formatter that forgets to escape loses its *formatting*, not its message.
It logs a warning naming the event type, so the bad formatter still gets found
rather than papered over.

Deliberately narrow: only that error is retried. A "chat not found" is not
fixed by dropping markup, and retrying every 400 would double every genuine
failure.

**And the site that was actually failing** now escapes its strategy, so the
message keeps its bold header instead of falling back to plain text.

## Found alongside: 45 push notifications for one condition

The same log showed `close_refused` sent **45 times for one trade in 45
seconds** during demo 4, one per second for as long as AutoTrading was off.

That was a decision made an hour earlier, in the log-throttle change: the log
was throttled and the alert deliberately was not, reasoning that "a message to
the operator is not log noise". True of the first one. The 46th is not
information — it is the operator's phone being used against him.

Retrying the close is still right: the target is still met and AutoTrading may
come back. Saying so every second is not. The alert now rides on the same
throttle decision as the log — keyed per trade AND per reason, so two trades
both refusing are both reported, and a *changed* reason is reported again.

## Worth checking

`ea_close` (1,311 sends in 30 days) and `tp1_hit` (617) are the highest-volume
alert types, and one trade got **3 `tp1_hit` alerts in 3 seconds** on
2026-09-01 while its EA was removed. Not investigated; a candidate for the same
"one condition, one message" treatment. Not urgent — duplicates are noise, and
this file's subject was messages that never arrived at all.
