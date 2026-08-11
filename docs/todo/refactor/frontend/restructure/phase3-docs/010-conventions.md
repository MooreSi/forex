# 010 — Document the conventions and the React decision

**Status:** not started
**Depends on:** phases 1 and 2 complete
**Touches money:** no — documentation only, no code changes
**Layer:** docs
**Leverage:** `docs/system/rules/` already holds the rules; this extends two files and adds one record

## Problem

Phases 1 and 2 leave four things that exist only in this pack, which `/spec done` deletes:

1. **The component convention** — written in 2/010 against one page, then tested against five more.
   It needs updating to what actually held, and it needs to live where someone adding a page will
   find it without being told the pack existed.
2. **What the closed boundary means going forward.** `docs/system/rules/30-architecture.md` lists four
   contracts enforced at zero. There are now five. Anyone adding a page needs to know their import
   will fail the suite, and why that is deliberate.
3. **The exemption register.** After 2/060 some files remain over 800 with recorded reasons. Those
   reasons live in PROGRESS.md, which is about to be deleted.
4. **The React decision.** Rejected on 2026-08-06 with specific reasoning. Without a record it gets
   re-proposed, re-argued and possibly re-decided differently on worse information — and the
   conditions that *would* justify it get lost too.

## Decision

Extend two existing `docs/system/rules/` files and add one decision record. Do not create a new
"frontend guide" — `docs/system/rules/` is numbered and read in order, and a fifth file competing with
`70-file-organisation.md` for the same subject is how documentation starts contradicting itself.

The React decision record goes in `docs/specs/` as part of spec 001 rather than `docs/system/rules/`: it is a
decision with a date and a rationale, not a rule to follow. `docs/todo/refactor/stage0/` is an audit trail and
must not be edited.

## What must NOT change

- **`docs/todo/refactor/stage0/` is not edited.** Not to correct it, not to append to it. It is an audit trail.
  FINISH_LINE.md's M2 note ("widget-level splits are cosmetic") stays exactly as written — spec 001
  already explains why this pack's justification differs rather than contradicting it.
- Existing `docs/system/rules/` numbering and structure. These are extensions, not rewrites.
- The tone of `docs/system/rules/`: short, specific, and it says why. A rule without its reason gets removed by
  whoever finds it inconvenient.
- No rule is documented that the code does not actually enforce. If phase 1 left an honest exception,
  the docs say so — a documented boundary the suite does not hold is exactly the "prints all good on
  every run" failure this repo was burned by.

## Tests first (TDD)

N/A — docs only.

One exception worth writing, because it is the class of failure this repo has already had:

- `tests/refactor/test_docs_match_the_gates.py::test_every_contract_enforced_at_zero_is_documented`
  — reads `import_contracts.py`, reads `docs/system/rules/30-architecture.md`, asserts the enforced-at-zero
  contracts named in the doc match the ones in the code.
- `tests/refactor/test_docs_match_the_gates.py::test_the_check_notices_an_undocumented_contract`
  — **negative control**.

This is optional if the owner considers it over-engineering; if skipped, say so in PROGRESS.md rather
than leaving it silently undone.

## What to do

1. **`docs/system/rules/70-file-organisation.md`** — add the component convention as it actually held across
   all six pages: pages-as-packages, `components/<domain>/` on the second caller,
   `components/shared/` for domain-free primitives. Name `pages/trading/` as the worked example. If
   the rule changed while being applied (2/010 explicitly permits that), document the rule that
   survived, not the one first written.
2. **`docs/system/rules/30-architecture.md`** — update the contract list to five enforced at zero. Say what the
   frontend→controllers boundary buys: no service call on the UI event loop, one place to rewire when
   a signature moves. Note that it went 99 → 59 → 0.
3. **The exemption register** — collect the reasons from PROGRESS.md into
   `70-file-organisation.md`: which files are over 800 by design and why (`runtime.py`,
   `mt5_bridge.py` and whatever phase 2 left, likely `chart.py`, `reversal_panel.py`, possibly
   `app.py`). An exemption with a reason is a decision; one without is an oversight, and the file
   cannot tell you which it is looking at.
4. **The React decision record** — append to `docs/specs/001-frontend-restructure.md`: what was
   proposed, what it was rejected for (Node runtime in a Python-only installer, a second VPS process,
   17,842 lines against a non-existent API, benefits that do not apply to a single-user localhost
   dashboard), and — most usefully — **what would change the answer**: a genuine need for
   multi-client access, a UI complexity NiceGUI cannot express, or an external consumer that forces
   an HTTP API into existence anyway. Note that phase 1 is the prerequisite either way, so the option
   is now cheaper than it was.
5. **CHANGELOG.md** — an internal entry. Structure changed, behaviour did not.
6. **`docs/specs/001-frontend-restructure.md`** — fill the Verification checklist, Status → Shipped.
7. `python -m tools.checks all`.

## Where

- `docs/system/rules/70-file-organisation.md` — component convention + exemption register
- `docs/system/rules/30-architecture.md` — the fifth contract at zero
- `docs/specs/001-frontend-restructure.md` — React decision record; Verification; Status
- `CHANGELOG.md` — internal entry
- `tests/refactor/test_docs_match_the_gates.py` — optional, see above

## Acceptance

- A session that has never seen this pack can add a new page correctly from `docs/system/rules/` alone.
- The contract list in the docs matches the code — ideally asserted by a test.
- Every over-800 file has a written reason.
- The React decision is findable, dated, and states what would change it.
- Spec 001 Status is `Shipped` with its Verification checklist filled in honestly — including the
  demo-session line for phase-1 task 020.
- `python -m tools.checks all` green, output pasted into PROGRESS.md.

## Notes

- Write this from **what shipped**, not from these task files. If phase 2 left `app.py` at 900 lines
  and two pages unsplit, that is what the docs say. A convention describing work that did not happen
  is worse than none — it is the thing that makes the next reader trust the wrong map.
- After this task, `/spec done` verifies, harvests anything still missing, and deletes
  `docs/todo/refactor/frontend/restructure/`. Check nothing needed survives only in PROGRESS.md first.
