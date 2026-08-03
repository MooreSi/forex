# SPEC-NNN — <short title>

**Status:** Draft | Approved | Building | Shipped | Abandoned
**Owner:** <who decides>
**Touches money:** yes / no  ← if yes, this needs sign-off and a demo session
**Created:** YYYY-MM-DD

---

## Problem

What is wrong or missing today, in plain terms. If there is an incident behind
it, say what happened and when.

## Goal

One paragraph. What is true after this ships that is not true now.

## Non-goals

What this deliberately does not do. This section prevents scope creep more
reliably than any other part of a spec — be specific.

## What must NOT change

The most important section in this repo.

- Which behaviour stays byte-identical?
- Which defaults must not move?
- Which tests must pass unmodified?

If this change touches order placement, closing, or sizing, list every
affected surface here and note the required sign-off.

## Design

How it works. Include the shape of the data and the boundary it sits on
(controller? service? repo?). Name the files.

## Test plan

Write this **before** the code. For each behaviour:

| Behaviour | Test | Type |
|---|---|---|
| default is unchanged | `test_..._is_still_X` | regression |
| the new path is wired | `test_..._follows_the_...` | wiring |
| bad input is rejected | `test_..._clamps` | boundary |

Include the negative controls: how would you know the test can fail?

## Rollout

- Is this behind a toggle?
- What does the user see the first time?
- How is it reverted if wrong?

## Open questions

Things the owner must decide. Do not guess these silently — if you proceed
under an assumption, write the assumption here.

## Verification

Filled in when shipped:

- [ ] full suite green
- [ ] all four gates green
- [ ] app boots and serves
- [ ] no real or demo order touched by this work or its tests
