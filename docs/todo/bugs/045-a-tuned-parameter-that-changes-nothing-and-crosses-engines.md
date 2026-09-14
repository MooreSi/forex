# 045 — `allow_asian` is tuned, logged, clamped, and read by nothing that acts on it

**Status:** found 2026-09-12 by reading the live Bounce database while
measuring `docs/simon-handover/033`. **Not fixed** — both available fixes
change which signals an engine generates, which is the owner's call.
**Touches money:** not today, and that is the finding. It was *meant* to.
**Severity:** low in effect, high in what it implies — an AI tuner has been
spending decisions on a lever that is not connected to anything.

## What the parameter claims to do

`adaptive_params.PARAMS["allow_asian"]`:

> *"Enable signals during Asian session (0 = off, 1 = on) — Asian signals
> require trend alignment"*

Claude's batch tuner may set it after every ten closed trades, and
`test_signal_learn.py` names it explicitly in the prompt
(*"allow_asian and allow_counter_bias must be exactly 0 or 1"*).

**It did.** In the live Bounce database, `ap:allow_asian` is `0.0`, written on
**2026-07-24 09:12** by `batch_analysis:10_trades`. Read plainly, the engine's
own tuner decided five weeks ago to stop trading the Asian session.

## What happened next

The Bounce engine generated **65 Asian-session signals** — more than any other
session, and 38% of the 173 it has ever produced.

## Why

`allow_asian` has exactly one reader:

```
test_signal/signal_generator.py:54    asian_allowed = ap.get("allow_asian") >= 0.5
                              :59        "asian": "good" if asian_allowed else "low",
```

— inside `session_quality`, whose only other consumer is `session_is_active`.
**Neither is called anywhere in the Bounce engine.** `generate` decides the
session question with its own inline rule (section 7c, now
`_gates.asian_counter_bias_blocks`), which never consults this parameter.

So the switch is not wired to the engine that owns it.

## And the one place it IS wired is another engine

Both functions are imported by the **Breakout** engine, which re-exports them
at `breakout_signal/signal_generator.py:31` and calls one of them for real:

```
breakout_signal_velocity.py:55        if not session_is_active(session):
                           :56            return
                           :58        if session == "asian":
                           :59            return
```

So a *Bounce* parameter, tuned by *Bounce*'s Claude reviewer from *Bounce*
trade outcomes, decides how the *Breakout* engine grades its sessions — and
even there it changes nothing, because the next two lines refuse the Asian
session unconditionally whatever the grade says.

Net effect across the whole app: **zero.** The parameter cannot change any
behaviour at either engine.

Worth stating against what the engines domain README says today:

> *"Each owns an isolated SQLite database, its own adaptive parameters, and its
> own ML model, with no cross-training."*

The databases and the models are indeed isolated. The parameters are not:
`session_quality` reads the Bounce store on the Breakout engine's behalf.

## Why it matters even though nothing moved

1. **The tuner is being graded on a lever that is not connected.** Every batch
   analysis that reasons about the Asian session and answers `allow_asian` has
   spent a decision on nothing, and the learning history in the UI shows the
   change as if it took effect.
2. **Anyone reading the DB gets the wrong answer.** `ap:allow_asian = 0.0` says
   the Asian session is off. It is the engine's busiest session.
3. **It is a live trap.** Wire `session_is_active` into `generate` — an obvious
   tidy-up — and 38% of this engine's signals disappear at once, on the
   strength of a decision made by an AI five weeks ago that nobody has ever
   seen take effect.

## The two fixes, both the owner's

1. **Disconnect it.** Delete `allow_asian` from `PARAMS` and from the tuner
   prompt, and let `session_quality` grade Asia the same as London. Honest, and
   it removes the trap. It also removes a lever he may want.
2. **Connect it.** Have `generate` consult `session_is_active`, which turns the
   engine's Asian session OFF immediately, because the stored value is 0.0.

Either changes which signals get generated, so neither is an unattended edit.
**Decide it alongside `docs/simon-handover/033`** — that file is already about
whether this engine should trade the Asian session at all, and this parameter
is the same question asked in a place nobody was reading.

## Related

* `docs/simon-handover/033` — the two engines disagree about the Asian session.
* `docs/simon-handover/034` — the Bounce engine has produced no signal since
  2026-08-27, also found in this pass.
* `tests/test_signal/test_generate_gates.py` — the gates `generate` actually
  consults, pinned 2026-09-12.


---

## What the Bounce engine's removal does and does not settle (2026-09-14)

The engine is stopped (`docs/todo/bugs/046`), so **the tuner half is gone**: no
Bounce batch analysis runs, so nothing spends a decision on `allow_asian` any
more, and nobody will read `ap:allow_asian = 0.0` as a statement about a
running engine.

**The cross-engine half is not.** `session_quality` still lives in
`test_signal/signal_generator.py`, still reads `ap.get("allow_asian")` from the
Bounce database, and is still imported and called by
`breakout_signal_velocity.py` — which is a running engine. So a stopped
engine's stored parameter is still consulted on the Breakout engine's path.

It still changes nothing, for the same reason as before: the line after the
call refuses the Asian session unconditionally. But the coupling is real, it
now crosses from a **retired** engine into a live one, and the cheapest way to
end it is to move `get_session`/`session_quality`/`session_is_active` somewhere
neither engine owns — which is also what `docs/todo/bugs/057` needs.

---

## Resolved by deletion, 2026-09-14

The Bounce engine's code was deleted (`docs/todo/bugs/046`), and its
`adaptive_params` catalogue with it. There is no longer an `allow_asian` for
anything to read.

**The cross-engine coupling is ended, not re-plumbed.** `session_quality` moved
to `services/market/sessions.py` and no longer reads an adaptive parameter at
all. The value that parameter actually held — `0.0`, which graded the Asian
session `"low"` — is now a named constant, `ASIAN_SESSION_QUALITY`, with the
history in the module docstring. Today's behaviour is preserved exactly.

Two things this does not do:

* It does not settle whether the Asian session **should** grade low. That is
  still a decision, and it is now a one-word edit in one place rather than a
  number in a retired engine's database. The only live caller,
  `breakout_signal_velocity`, still refuses the Asian session unconditionally
  on the line after it asks, so the grading changes nothing either way until
  that changes too.
* It does not touch `docs/todo/bugs/057`. `market/sessions.py` is still only
  one of four disagreeing definitions of a trading session; moving it did not
  reconcile it with the other three, and deliberately so.
