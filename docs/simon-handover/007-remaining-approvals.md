# Q007 — Two remaining approvals

**Who answers:** Simon. Two smaller yes/no items that came up during the
build, gathered here so everything you answer lives in this folder.

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

**ANSWER:**


---

## 2 of 2 — What does "handed over" mean?

The finish line we've been building toward:

- **A. A handover session: Darren walks you through it, you watch the
  safety demos on your demo account, sign off, and take the keys**
  *(recommended — this is what session-agenda.md is)*
- **B. Full self-serve: you want to be able to set it up and run it
  entirely alone from the docs, no session needed** *(the guides support
  this too, but it raises the bar before handover)*

**ANSWER:**

