# What the refactor actually changed

**For:** Simon · **Written:** 2026-08-26 · Keeper doc, not a work log.

Plain English, and honest in both directions. Every number here was measured
against the code, not remembered.

---

## The one-line version

The refactor made the app **safer to change** — not safer to trade. Nothing
about how it decides, sizes or closes a trade was altered, on purpose. What you
got is the ability to make the next change without guessing what it breaks.

---

## What is genuinely better

**The big file that did everything is broken up.** One file, `engine.py`, was
3,165 lines and held the trading loop, the Telegram bot, the signal scanner and
more. It is now 1,575 lines with the rest moved into parts that have names. The
Trading screen went from a single 3,290-line file to ten modules, the largest
704 lines.

**There is now a layer between the screens and the database.** 13 "controller"
modules, from none. The rule — screens never touch the database directly — is
enforced by tests that fail the build, not by good intentions.

**Database changes are reviewable.** Around 90 scattered, ad-hoc table changes
became **28 numbered steps** that run in order, stamp their version, and are
tested against old copies of your data. Verified: all 192 statements apply
cleanly to a fresh database.

**The tests mean something now.** 1,824 → **2,702 tests**. The number matters
less than this: 13 files that looked like tests but checked *nothing* were
deleted, and a gate makes that impossible to reintroduce.

**3,473 lines of dead code deleted** — three copies of the database layer that
nothing used, while everyone assumed they were live.

**Things that simply were not there before:** daily database backups, a login on
the dashboard, the dashboard reachable only from this machine, and a complete
offline mode (fake broker, market, Telegram, news, AI) that can run a signal
from arrival to close without touching a broker.

**11 automatic guards** that fail the build when the structure slips — file
sizes, dead modules, layer boundaries, test coverage.

---

## What it cost

**Moving files around broke things quietly.** Nine places worked out where they
were on disk by counting folders — right from their old home, wrong from the
new one. That is what broke your **Restart button**, hid the **admin console**,
made every EA report as out of date, and made "which version is this client
running" answer *unknown*. All fixed on 2026-08-26, but they sat there unnoticed
because nothing exercised those paths until you did.

**The frontend split never happened.** The Settings screen was 3,204 lines and
is now **3,487** — it grew. That row on the readiness checklist is still
unticked, and honestly marked as maintenance debt rather than a money risk.

**The automatic checks have never run on this repository.** Not once. The green
run the checklist points at happened on Darren's copy, three weeks before the
current code existed. Turning them on needs one click from you (see
[STATUS](../todo/upstream-merge/STATUS.md)).

---

## What is still not done

The money-path work — never place the same order twice, keep the app's books
matching the broker's, never record a close the broker refused, safety brakes on
by default. It is designed and test-planned. **It is not built.** It ships only
with you watching it on your demo account, which is Part B of
[session-agenda.md](session-agenda.md).

The checklist says it plainly, and it is still true: *the app must not be
treated as handed over until this line is green.*

---

## The fair summary

If you are asking "is my app better?" — it is more likely to survive its next
change, and much more likely to tell you when something is wrong. It does not
trade any better or any more safely than before, because that was deliberately
out of scope.

The two things you would actually *feel* — a maintainable Settings screen, and
the order-safety work — are the two still outstanding.
