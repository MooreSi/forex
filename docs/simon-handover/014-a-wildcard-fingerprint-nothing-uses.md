# 014 — a wildcard licence fingerprint that nothing uses

**Decision needed:** keep it or delete it
**Urgency:** low, but it is a security question, so it should not just sit
**Money:** no

## What is there

`backend/src/config/licence/fingerprint.py` defines:

```python
TEST_WILDCARD = "TEST_WILDCARD_000000000000000000000000"

def is_test_wildcard(fingerprint: str) -> bool:
    return fingerprint == TEST_WILDCARD
```

and its module docstring said, until 2026-08-31:

> The wildcard fingerprint ... is reserved for internal testing and **bypasses
> all hardware checks.**

## What is actually true

**Nothing in this application consults either of them.** I searched the whole
tree: the only occurrences are the definition itself and that docstring. So
there is no bypass in the code today, and no licence you have issued can work
on a machine it was not issued for.

## Why I am raising it rather than just deleting it

Two reasons pull opposite ways.

**For deleting:** a constant named "wildcard", next to a ready-made predicate,
described in a docstring as bypassing hardware checks, is an invitation. The
next person who reads it will reasonably conclude the behaviour is supported
and was lost, and wire it back up. At that point one licence works on every
machine — and it would look like a restoration, not a change.

**For keeping:** the docstring says this file "produces the same
registration_id as KeyGen/Registration/fingerprint.py". If your KeyGen side
defines the same constant, deleting it here makes the two files diverge, and
that divergence is the sort that goes unnoticed until a licence will not
verify. I cannot see the KeyGen tree from here to check.

## What I did in the meantime

Nothing that changes behaviour.

1. **Corrected the docstring** to say what is true: nothing consults these, and
   wiring them up is a licence bypass needing your sign-off.
2. **Added a test that fails if anything starts consulting them** —
   `tests/licence/test_fingerprint.py::TestTheWildcardIsNotWired`. Wiring it up
   is now a deliberate act that turns the suite red first, rather than a quiet
   one-line change.

## What I need from you

Just one answer: **does KeyGen define `TEST_WILDCARD` too?**

- **Yes** → leave it exactly as it is. The test and the corrected docstring are
  the right end state.
- **No** → I will delete both the constant and the predicate. Dead code that
  looks like a master key is worth removing.

Related: the licence signing itself is sound — `config/licence/verify.py` is
Ed25519, public-key-only, and the old `CHANGEME-BEFORE-PRODUCTION` secret is
gone from the tree. Every path that stores a licence verifies its signature
first, pinned by `tests/licence/test_no_unverified_save.py`.


---

## ANSWERED, 2026-09-01 — removed

> **"There should be no master key, the keygen is kept in a separate folder
> purposely."**

`TEST_WILDCARD` and `is_test_wildcard()` are deleted, and the module docstring
now records that there is no wildcard by design, with the reason.

The test that guarded them is replaced by a stronger one. Rather than checking
nothing *uses* the hook, it checks the hook does not exist — and that no
equivalent has reappeared under another name (`MASTER_FINGERPRINT`,
`WILDCARD_MACHINE`, or the old names). A different name for the same idea is
the same problem.
