# 033 — A stale EA build was only ever a log line

**Status:** **FIXED 2026-09-09** — the top-bar EA badge now shows it. The
underlying deploy step is unchanged and still has to be run.
**Money:** indirectly, and badly. Every EA fix since the last real compile is
absent while the app and the operator both believe it is running.
**Found:** live, from the owner: *"why does this still state 'per trade' when
it should be the total sum of all trades ... I have just recompiled and
reattached the EA"*.

## What happened

Global Harvest was fixed in the EA (bugs/027, v1.06) to sum across positions
instead of closing each one on its own profit. The owner recompiled, reattached
and saw the old behaviour: the panel still read `at $50.00 profit per trade`
and three positions clearing $50 between them were not harvested.

**The compile succeeded — it just compiled the wrong file.**
`tools/deploy_ea.sh` copies the repo's `.mq5` into MetaTrader's own Experts
folder; without it, MetaEditor rebuilds the copy already sitting there. The
result was a fresh `.ex5` stamped 12:44 today, still at v1.05.

The app had already worked this out and said so on every EA connection:

```
EA VERSION MISMATCH: terminal is running v1.05 (compiled 2026.09.09 12:44:17)
but this app ships EA source v1.06. The .ex5 is stale -- run
tools/deploy_ea.sh, then compile (F7).
```

**It is a WARNING, so it sat in a log nobody reads** while the fix appeared not
to work and the panel text was taken as evidence that the change had not landed.

`deploy_ea.sh`'s own header records this class of failure costing a full day
once already: *"a batch of EA fixes was written, reviewed, committed, and
'recompiled' several times, while the terminal kept compiling a source from
three weeks earlier."* **That makes twice.**

## The fix

`ea_bridge.ea_build_status()` exposes the handshake result, and
`ea_badge_state()` turns it into the top-bar badge: **amber, "EA STALE BUILD"**,
with a tooltip naming both versions and the exact remedy. Stale outranks
connected — green on a stale build is the screen contradicting the log — and
"not connected" outranks both, since a disconnected EA is running no build at
all.

Unknown is deliberately NOT stale. `ea_version_ok` is None when there is no EA
source to compare against, and crying wolf there is how a warning stops being
read in the first place.

13 tests. Five mutants killed — including one that survived a first attempt:
the badge test originally grepped the header's source for "orange", and a
mutation making the amber branch unreachable left the string in place and
passed. The decision was extracted into a pure function and is now asserted
directly.

## What this does NOT fix

The deploy step is still manual and still easy to skip. The badge tells you
afterwards; it does not compile anything. The automated path
(`backend/src/services/broker/ea_deploy.py`) runs after a self-update, so a
remote client is covered — a developer pressing F7 on their own machine is not.

**Worth considering:** have the app refuse to treat an EA as healthy for
template strategies while the build is stale, rather than only colouring a
badge. That is a behaviour change on the money path and wants the owner's call,
so it is recorded here rather than done.
