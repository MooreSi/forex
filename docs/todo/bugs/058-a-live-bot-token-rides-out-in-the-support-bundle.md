# 058 — A live Telegram bot token leaves the machine in the diagnostics upload

**Status:** **CLOSED 2026-09-13.** Code fixed 2026-09-12, test-first, four
mutants killed. **The owner has decided not to rotate the token** — his call,
recorded below with what that accepts.
**Touches money:** no, and that undersells it. A bot token is control of the
bot: read every message it can see, and post as it.
**Severity:** a live credential, written to disk 7,245 times a day and
transmitted off the machine on request.

## What was leaking

`cluster/remote/client._build_diagnostics` uploads the last 3,000 raw log lines
to the admin server when diagnostics are requested. httpx logs the full request
URL at INFO on every Telegram poll, and the token is in the path:

```
GET https://api.telegram.org/bot<id>:<secret>/getUpdates?offset=... "HTTP/1.1 200 OK"
```

In the live log on 2026-09-12: **7,245 lines carried one**, and **166 of the
last 3,000** — which is exactly the slice that gets uploaded.

## Why the existing redactions missed it

Two redactions were already accepted and built for this exact upload, both from
Q005 #1: the MT5 login (`mask_account`, after the connect line put the account
number, broker and balance into every uploaded log) and email recipients
(`mask_email`). Both work.

They were built for the two things that question happened to name. The bot
token was on the same pages, in far more lines than either, and nobody looked
for a third.

The **filtered** half of the payload was safe by accident: `_DIAG_NOISY` drops
any line containing `"HTTP/1."`, which is every httpx line. `log_raw` is
verbatim and was not.

## The fix

`os_utils.scrub_log_secrets`, beside the two masks it belongs with, applied to
both halves of the payload.

**The bot id is kept; only the secret goes.** Support has to know which bot a
log came from, the number before the colon is public in any Telegram username
lookup, and the half after it is the credential.

It is deliberately narrow. A rule that went after anything token-shaped would
also redact `name='Task-1004'` — 174 lines of the live log look like that, and
those lines are the evidence for bugs/030's event-loop stalls.

Four mutants killed, including "return the text unchanged", "match only the
first occurrence", and a capture-group shift that would have eaten the bot id
along with the secret.

## What the fix does NOT do, and this is the part for the owner

**It does not un-send anything.** The token has been in every uploaded
diagnostics bundle up to now, and it is still in every log file on disk —
7,245 lines in today's alone, and the rotated files going back to 2026-08-12.

## The decision, 2026-09-13

**The owner has decided not to rotate the token.** Recorded as taken, and this
file is closed on it.

What that accepts, stated plainly so it is a decision and not an oversight:

* the token is in every log file on disk, back to 2026-08-12, and in every
  diagnostics bundle uploaded before 2026-09-12;
* anyone who has one of those files has full control of the bot — read what it
  can see, post as it;
* nothing further is exposed from here: the scrub means no future bundle
  carries it.

That is a reasonable position if the admin server is trusted and the bundles
have only ever gone there, which is the case as far as this repo can tell.

**One option left on the table, not taken and not urgent.** The scrub stops the
token *leaving*; it does not stop httpx *writing* it, so the log files keep
accumulating it at roughly 7,000 lines a day. A logging filter using the same
`scrub_log_secrets` would redact it as each line is written, keeping the
per-request line that several investigations have used while never putting the
secret on disk. It is perhaps twenty lines and it touches every log record,
which is why it is written here rather than done: it is a change to the app's
logging for a risk the owner has just accepted. Ask for it if you want it.
