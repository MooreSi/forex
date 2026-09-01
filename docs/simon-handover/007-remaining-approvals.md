# Q007 — Two remaining approvals

**Who answers:** Simon. Two smaller yes/no items that came up during the
build, gathered here so everything you answer lives in this folder.
**Status:** **ANSWERED 2026-08-25.** 1: **B** — Simon issues the dev licence
from the admin console. 2: **B** — full self-serve is the handover bar.

---

## 1 of 2 — The practice-mode licence

Practice mode ("debug mode") needed a licence to boot, because the licence
check is never bypassed — that's a hard rule. So a small tool was built that
generates a *genuine* licence for Darren's development machine, valid 30
days at a time, using the same generator your licences come from.

The thing to be aware of: that generator (and its secret) ship inside the
code, so anyone with a copy of the code could always self-licence — this
tool doesn't create that exposure, it just uses it openly. Fixing the
exposure itself is the licence-security rework on the future roadmap.

- **A. Fine — Darren self-licensing for development is approved**
  *(recommended; already in use, expires every 30 days)*
- **B. Not fine — you'll issue Darren a licence from your admin server
  instead**

**ANSWER:** **B — Simon issues Darren's licence from the admin server.**
(Simon, 2026-08-25)

> **The question's premise is about to become false, and that is what decides
> it.** This question assumed "the generator and its secret ship inside the code,
> so anyone with a copy could always self-licence". The upstream merge closes
> exactly that hole: commit `7251656` **deletes `keygen.py`**, replaces it with
> `licence/verify.py` (Ed25519, public key only), and moves the private key
> outside the repo. After the merge, self-licensing from a code copy is no longer
> possible for anyone — which makes B the natural answer rather than an
> imposition, and A would mean deliberately reopening the hole the merge closes.
>
> **Concrete consequence to handle during the merge.** Three modules in this
> branch import the deleted `keygen`:
>
> | Import site | Fate |
> |---|---|
> | `backend/src/config/licence/guard.py:19` | Upstream re-homed it: verifies via the Ed25519 public key. Merge resolves it. |
> | `backend/src/services/cluster/remote/server.py:419` | Upstream re-homed it: signs through a `sign_fn` callback, private key outside the repo. Merge resolves it. |
> | `tools/generate_debug_licence.py:18` | **No upstream counterpart** — written after the fork, so the merge breaks it. |
>
> **Work this authorises:** rewrite `tools/generate_debug_licence.py` so it
> *requests* a licence for the dev machine rather than minting one, and Simon
> approves it from the admin console via the inline Telegram Approve buttons
> (6mo/1yr/2yr/3yr/Perpetual) that arrive with commit `7251656`. The rule that
> practice mode never bypasses the licence check is unchanged.


---

## 2 of 2 — What does "handed over" mean?

The finish line we've been building toward:

- **A. A handover session: Darren walks you through it, you watch the
  safety demos on your demo account, sign off, and take the keys**
  *(recommended — this is what session-agenda.md is)*
- **B. Full self-serve: you want to be able to set it up and run it
  entirely alone from the docs, no session needed** *(the guides support
  this too, but it raises the bar before handover)*

**ANSWER:** **B — full self-serve: Simon can set it up and run it alone from
the docs, no session needed.** (Simon, 2026-08-25)

> **Recorded honestly: this raises the bar, and it does not remove one
> requirement.** Choosing B means the documentation has to carry the whole
> setup-and-run path unaided, which is a larger job than option A's guided
> session. It also does **not** dissolve session-agenda **Part B**: the
> money-safety changes (B1-B6) must still be demonstrated on Simon's demo
> account with him watching before they ship. That is CLAUDE.md rule 1 and the
> golden rules, not a preference about handover style — no answer here can waive
> it.
>
> So the finish line is now: **self-serve docs good enough to install, configure
> and run the app with nobody else present, *plus* the Part B demo sitting for
> the money-touching work.** `readiness-checklist.md` and `session-agenda.md`
> should be updated to reflect the raised documentation bar.

