# Q005 — Four facts only you know

**Who answers:** Simon. These aren't choices — they're facts about how the
system has actually been run, which the code can't tell us. Each one has a
worst-case assumption we're working under; your answer either relaxes it or
confirms the work is needed.

How to answer: write what you know on each **ANSWER:** line. "Don't know"
is a useful answer too — it keeps the cautious assumption.

---

## 1 of 4 — Do the app's log files contain account details?

The log folders were empty in the copy we reviewed, so we couldn't check
whether logs capture account numbers or personal data. Meanwhile the
diagnostics feature can upload ~3,000 raw log lines to the admin server.

*Working assumption: logs may contain account numbers — treated as
sensitive.*

**ANSWER** *(have you seen account numbers / personal data in the logs?)*:


---

## 2 of 4 — Was the licence signing secret ever changed?

The licence generator still contains its original placeholder secret
(literally marked "CHANGE ME BEFORE PRODUCTION"). If it was never changed,
anyone with a copy of the code could forge a licence. This decides how
urgent the licence-security rework is.

*Working assumption: never changed (worst case).*

**ANSWER** *(did you ever change it? roughly how many licences exist out
there?)*:


---

## 3 of 4 — Is the remote auto-update client running anywhere?

The insecure update channel is now off by default (see Q001 #5) — but if
some installed copy out there still runs the old client, that changes the
urgency.

*Working assumption: not in use anywhere.*

**ANSWER** *(does any machine still run the update/remote-admin client?)*:


---

## 4 of 4 — Is old-data clean-up ("retention") switched on anywhere?

There's an optional feature that prunes old trades from the database. It's
off by default. If it's off everywhere, a couple of known clean-up bugs are
dormant rather than live.

*Working assumption: off everywhere.*

**ANSWER** *(did you ever switch retention on?)*:

