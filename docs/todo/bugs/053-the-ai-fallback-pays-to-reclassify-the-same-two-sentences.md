# 053 — The AI fallback has recovered nothing in 61 calls, 41 of them on two sentences

**Status:** found 2026-09-12 auditing `ai_fallback_checked`. **Not fixed** — the
obvious fix changes what the signal path does with a repeated message, and
"this text has been classified before" is not the same claim as "this message
has".
**Touches money:** no. It is an API bill and a feature that has not earned its
place yet.
**Severity:** low. Written down because a recovery path that has never
recovered anything should be known about before anyone relies on it.

## What the table says

2026-09-09 to 2026-09-11: **61** paid AI classification calls, over **19**
distinct message texts. Two of them account for 41:

```
 31  'PREPARE FOR BUY LIMITS'
 10  'PREPARE FOR SELL LIMITS'
```

`ai_recovered_signals` holds **0 rows**. In 61 calls the fallback has never
turned an unparsed message into a signal.

## Why the same sentence is paid for 31 times

`recovered_repo.has_ai_fallback_check` keys the guard on
`(tg_message_id, text_hash)`:

```python
"SELECT 1 FROM ai_fallback_checked WHERE tg_message_id=? AND text_hash=?"
```

That is deliberate and its docstring says so: the pair means an **edited**
message gets re-checked, which is right — an edit can turn chatter into a
signal. The consequence nobody costed is that the channel posts the same
heads-up sentence before every setup, each as a new message with a new id, and
each one is a new call.

## Why the obvious fix is not obviously right

Keying on the text alone would collapse 41 calls into 2. It would also mean
that the second time a channel posts the same signal text, the app does not ask
about it. For "PREPARE FOR BUY LIMITS" that is clearly safe. For a channel that
posts an identical `XAUUSD BUY 4350 SL 4345 TP 4360` twice in a week, it is a
missed trade, and this fallback exists precisely for messages the parser could
not read.

Two shapes that keep both properties:

1. **Remember the verdict, not just the check.** Skip only when this exact text
   has previously been classified *"not a signal"*. A text that once produced a
   signal is always re-asked. Needs a verdict column; the table stores only
   that a check happened.
2. **Skip texts with no numbers in them at all.** "PREPARE FOR BUY LIMITS" has
   nothing to parse into an order, so no AI call could produce one. Cheap, and
   it never touches a message that could be a signal.

Option 2 is nearly free and has no failure mode that costs a trade, but it is
still a change to what reaches the signal path, on the channel that produces
most of this account's real orders.

## The other half: it has recovered nothing

61 calls, 0 recoveries, and `channel_unrecognised_messages` is also empty. So
on the current evidence the parser is not missing signals that the AI can find
— which is a good result for the parser and an open question about whether this
path is earning its cost.

Three days is not enough to retire it. It is enough to say it should be
measured rather than assumed, and to note that the counter which would show it
working (`ai_recovered_signals`) is the one to watch.
