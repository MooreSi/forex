# 050 — An alert that only fires during an outage is an alert that never arrives

**Status:** found 2026-09-12 reading `vantage_telegram_log` for a recurrence of
bugs/020. **Half fixed the same day:** the repetition is damped (one alert per
ticket per episode, four mutants killed). The part that matters — an alert that
cannot be delivered during the outage that raised it — is **open**, because the
answer is a retry queue or a reconnect summary and that is a design choice.
**Touches money:** no. Nothing is mis-booked; the guard underneath works
(bugs/025 is now live-verified because of this same evidence).
**Severity:** the app's loudest safety warning is silent in exactly the
situation that raises it.

## What the log shows

2026-09-07, 01:15:17 to 01:21:03 UTC. Trade `c55bed33-7bc8-4d`:

```
17 x ea_close_unverified   status=error
      ... [Errno 8] nodename nor servname provided, or not known
```

Seventeen alerts, one every eleven seconds, all for the same ticket, and
**every one failed to send.**

## Two separate problems, and the second is the one that matters

### 1. It repeats per poll, with no damper

`_on_trade_closed` raises this alert every time the EA reports a ticket it
cannot verify, and the EA's `CheckForClosures` re-reports the same missing
ticket on every cycle. So the alert count is "how long the condition lasted,
divided by eleven seconds". Seventeen here; it would have been a hundred if the
outage had lasted twenty minutes.

This is the same shape as bugs/035 (a declined SL adjustment looping forever)
and the flap that `withdraw_count` damps in limit-orders/050. The pattern is
known and the remedy is known: alert on the first occurrence per ticket, then
go quiet.

**Done, 2026-09-12.** `_events._AlertedTickets`: one alert per ticket, cleared
when that ticket next verifies, so a second episode on the same ticket is new
news and says so. **The guard itself is not damped** — every repeat still asks
the broker and still books nothing; going quiet about a condition is not
deciding it has passed, and that distinction has its own test. Four cases in
`tests/services/broker/test_ea_close_without_a_price.py::TestItSaysItOncePerTicket`.

### 2. The cause of the alert is the cause of its failure

The condition is *"the EA says this position is gone and the broker cannot
confirm it"*. The commonest reason the broker cannot confirm anything is that
the machine cannot reach it — and Telegram is reached the same way. So the
alert designed for exactly this situation is the one guaranteed not to be
delivered in it.

There is no retry and no catch-up. Once the network returns, nothing re-sends,
and nothing says "while you were offline, seventeen closes could not be
verified". The only record is `status='error'` rows in a table nobody opens.

On 2026-09-07 that cost nothing: the trade resolved on its own nine minutes
later at -$48.00, and the guard's whole job — refusing to book a fabricated
-$44,000 — was done regardless of whether anyone was told. The next one might
not resolve itself, and the outcome would look identical from the outside:
silence.

## What it needs

1. ~~**Damp it**: one alert per ticket per condition, not one per poll.~~
   **Done 2026-09-12**, see above.
2. **Survive the outage**: either a small retry queue for failed protective
   alerts, or a startup/reconnect summary — *"N alerts failed to send while
   offline, most recent: …"*. The second is much simpler and covers the case
   that matters, which is the operator finding out at all.
3. **Make the failures visible somewhere a person looks.** 17 rows of
   `status='error'` in `vantage_telegram_log` is the entire current record.

Which of those, and whether a failed protective alert should also show on the
top bar, is a design question rather than a bug fix — which is why this is
filed rather than done.

## Related

* `docs/todo/bugs/025` — the guard whose alert this is. Verified live by the
  same evidence.
* `docs/todo/bugs/020` — Telegram alerts silently rejected, 2026-09-01. This
  is a different cause (transport down, not payload rejected) with the same
  ending: the operator is not told.
* `docs/todo/bugs/035` — the same per-poll repetition, fixed there.
