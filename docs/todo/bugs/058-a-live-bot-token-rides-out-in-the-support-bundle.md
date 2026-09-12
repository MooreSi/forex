# 058 — A live Telegram bot token leaves the machine in the diagnostics upload

**Status:** found and **FIXED 2026-09-12**, test-first, four mutants killed.
**The token itself still needs rotating** — see the bottom. That part is the
owner's.
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

Two things worth deciding:

1. **Rotate the bot token** (`/revoke` then `/token` with BotFather, then
   update it in Settings). That is the only action that makes a leaked token
   harmless, and it costs one restart.
2. **Decide about the log files themselves.** The fix stops the token leaving
   in a bundle; it does not stop httpx writing it. Quietening the httpx logger
   to WARNING would stop it at source, but that also removes the per-request
   line that several investigations have used. Worth a conscious choice rather
   than a default.

Neither is urgent if the admin server is trusted and the bundles have only ever
gone there. Both are cheap.
