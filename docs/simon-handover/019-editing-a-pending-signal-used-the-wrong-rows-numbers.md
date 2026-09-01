# 019 — editing a pending signal used another row's numbers

**Status:** found and fixed 2026-09-01. No decision needed — but worth reading,
because you may have seen the symptom.
**Money:** yes. It could write a wrong stop loss and wrong targets, and push
them to an open trade.

## What was wrong

The Pending Signals screen lists your unexecuted signals, each with an Edit
form — direction, entry range, stop loss, eight targets, notes.

The Save button on **every** row read the values from the **last** row's boxes.

So with three pending signals: open the first, change its stop loss, press
Save, and the app wrote the *third* signal's entry, stop and targets onto the
first one. The signal id was correct — only the numbers came from the wrong
place.

`update_signal` also pushes SL/TP through to a matching open trade, so this
could move a live stop to a number belonging to a different setup.

## The symptom you might have noticed

The green **"Saved"** confirmation appeared on the wrong row. It looks like a
rendering glitch — a bit of the screen not refreshing. It was not: it was the
same fault, showing.

If you ever edited a pending signal and thought the numbers looked wrong
afterwards, this is why, and it was not you.

## Why it happened

A callback written inside a loop remembers *where* a value lives, not what it
was at the time. By the time you click, the loop has finished and every
callback sees the last row.

The app already does this correctly elsewhere — the Partial Close button on the
Active Trades screen captures both its trade and its lot-size box. The Pending
Signals editor captured the signal id and not its fourteen input boxes. One
oversight in one place, not a pattern.

## What is in place now

The fix is the same idiom used on the working screen. On top of that there is
now a check that fails the build if any callback anywhere in the app reads a
loop's variables late — so this cannot come back quietly in a different screen.
It runs with the other checks and reads clean today.

Three places are on a short allowlist because their callbacks run immediately
rather than on a click, which cannot go wrong; each has its reason recorded.

## What I could not tell you

**Whether it ever actually bit you.** Nothing is logged when it happens — the
edit succeeds, it just saves the wrong numbers. If you have edited pending
signals in the past and a stop loss or target ever looked wrong afterwards,
that would be this.
