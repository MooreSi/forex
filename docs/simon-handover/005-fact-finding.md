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
**Yes — confirmed from evidence, not memory. (2026-08-25)**

> Checked against Simon's own captured logs in `~/Downloads/` (contents never
> reproduced here; only shapes and counts).
>
> - **The MT5 account number, broker server and balance are logged at INFO on
>   every bridge connection.** Source: `mt5_bridge.py:179` —
>   `"Connected to MT5. Login: %s, Server: %s, Balance: %.2f %s"`.
>   `forex_log_Simon_-_VPS-4.txt` carries six such lines
>   (`Server: VantageMarkets-Demo`).
> - **Recipient email addresses are logged** by `email_service` on every send
>   (two lines in `forex_log_Simon_-_VPS.txt`).
> - **No passwords, API keys or licence keys were found** in any of the six
>   captured files. The only `token` lines are RemoteClient *status* messages
>   ("Token rejected — awaiting admin approval", "Token revoked by
>   administrator"), which carry no token value.
>
> **So the cautious working assumption is now a verified fact**, and the
> consequence is real: the diagnostics feature uploads ~3,000 raw log lines to
> the admin server, which means it ships the MT5 account number and balance.
>
> **Follow-up work this authorises:** redact or omit the login number at the
> `mt5_bridge.py:179` call site (log a masked form), and redact recipient
> addresses in `email_service`, before the diagnostics upload is used again.


---

## 2 of 4 — Was the licence signing secret ever changed?

The licence generator still contains its original placeholder secret
(literally marked "CHANGE ME BEFORE PRODUCTION"). If it was never changed,
anyone with a copy of the code could forge a licence. This decides how
urgent the licence-security rework is.

*Working assumption: never changed (worst case).*

**ANSWER** *(did you ever change it? roughly how many licences exist out
there?)*:
**Never changed — and the live app has already fixed it. Licences: just
Simon's own, 1-3 machines. (Simon + evidence, 2026-08-25)**

> **Evidence.** This branch's `backend/src/config/licence/keygen.py` still holds
> a 46-character literal `_SERVER_SECRET` matching placeholder wording (value not
> reproduced). Upstream commit `7251656` (2026-08-02) states it outright: keygen
> held **one hardcoded HMAC secret used to both generate and verify**, shipped in
> the same file to every client, in a public repo — so anyone reading it could
> mint a valid licence.
>
> **Already fixed upstream, arriving with the merge.** `licence/verify.py`
> (Ed25519, public key only) replaces `keygen.py`, which is **deleted** along
> with the dead REST/JWT flow (`client.py`, `jwt_public.pem`, `public.pem`,
> `server.crt`) that `guard.py`'s `enforce()` never called. The private key lives
> outside the repo in `KeyGen/licence_signing.py` and is never imported into
> shipped code. Registration approval moved to inline Telegram Approve/Reject
> buttons. Commit `9b4b311` auto-heals old HMAC keys after the migration.
>
> **Blast radius: small.** Simon confirms only his own 1-3 machines are licensed,
> so the exposure was largely theoretical and auto-heal covers the re-signing.
>
> **Note for Q002 #2:** this resolves that question by deletion — the parked
> `licence/client` phone-home code is removed by the merge.


---

## 3 of 4 — Is the remote auto-update client running anywhere?

The insecure update channel is now off by default (see Q001 #5) — but if
some installed copy out there still runs the old client, that changes the
urgency.

*Working assumption: not in use anywhere.*

**ANSWER** *(does any machine still run the update/remote-admin client?)*:
**Yes — the admin console is in active use. The working assumption of "not in
use anywhere" was wrong. (Simon, 2026-08-25)**

> **Simon, in his own words:** "the remote admin console allows me to see which
> remote clients/users are online, for how long and their licence key info, i can
> revoke the licence key info from the admin console so the admin console is now
> just used for licence key permissions and seeing which users are online. it is
> still in-use, any updates pushed are now pulled from github as opposed to being
> sent from the main server to the remote client, the push feature simply tells
> the remote client to connect to github and retrieve the most up to date commit."
>
> **Corroborated by evidence and by upstream code.** `forex_diag_windows.txt`
> (2026-06-29) shows the client live: `[RemoteClient] Agent started (connecting
> to 217.155.25.160:8443)`, LAN beacons, repeated registration requests, and a
> later "Token revoked by administrator". Upstream commit `0815cc6` (2026-08-02)
> is exactly the change Simon describes: the zip-streaming push
> (`MSG_UPDATE_BEGIN`/`MSG_UPDATE_END`, `_build_update_zip()`,
> `_apply_update()`) is **deleted** and replaced by a single `MSG_GIT_UPDATE`
> trigger that asks the client to run its own `apply_update()` git fetch.
>
> **This changes Q001 #5 — see the amendment recorded on that file.**


---

## 4 of 4 — Is old-data clean-up ("retention") switched on anywhere?

There's an optional feature that prunes old trades from the database. It's
off by default. If it's off everywhere, a couple of known clean-up bugs are
dormant rather than live.

*Working assumption: off everywhere.*

**ANSWER** *(did you ever switch retention on?)*:
**Never switched on. (Simon, 2026-08-25)**

> Confirms the working assumption, so the two known clean-up bugs are dormant
> rather than live and drop down the priority queue. Weakly corroborated: no
> retention / prune / purge setting was found in `forex_trader_demo.db`
> (40 tables) — though that is the demo copy, not the production database.

