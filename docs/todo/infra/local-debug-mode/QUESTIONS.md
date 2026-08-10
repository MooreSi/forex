# Local debug mode — decisions to confirm

Plain-English choices to settle before building. Each has a **recommendation** — you can say "go with
the recommendations" and only change what you disagree with. Numbers are starting points, not decided
values. Answer inline (write `ANSWER:` under each). Answered items stay, annotated — don't delete.

## The decisions (quick list)
1. Is the locally generated debug licence key OK? (needs Simon, not just Darren)
2. What format should scripted fake-data scenarios use?
3. How are the dashboard username/password first set?
4. Should fake order fills model slippage and partial-fill realism?
5. Confirm the debug DB is its own file, and the flag name.
6. Should debug mode auto-enable the signal engines and auto-execute?

---

## 1. Debug licence key — is generating a valid local key acceptable?

The golden rules ban adding "a licence or auth bypass, even for testing", so we will **not** edit
`guard.enforce()` or add a skip flag. Instead, a small tool would use the *existing* key generator
(`config/licence/keygen.py`) to write a genuinely valid key for the local machine — the real
verifier runs untouched. But that generator's secret ships in the repo, so this is Simon's call to
bless, because it documents (again) that anyone with the repo can self-licence. The alternative is
Simon issuing Darren a key from his admin server.

- **Generate locally, 30-day expiry, tool named `tools/generate_debug_licence.py` (Recommended)** —
  Darren is unblocked immediately; guard code untouched; expiry limits the artefact's life.
- **Simon issues a real key** — cleanest, but blocks all local work on Simon's availability, which
  is the exact dependency this pack exists to remove.

ANSWER:

## 2. Scenario format for fake ticks and fake signals

The fake bridge streams prices and the fake reader replays Telegram-style signal messages. Both
need scripted, deterministic scenarios (so e2e tests assert exact outcomes) plus a hands-free
default for just clicking around the UI.

- **JSON scenario files under `tools/debug_scenarios/`, plus a seeded random-walk default
  (Recommended)** — one scenario = tick script + signal script + expected outcome notes; e2e
  fixtures and the interactive app share the same files.
- **Hardcoded Python scenarios in the fakes** — less to build, but every new case is a code edit
  and the files can't be shared with Simon as documentation.

ANSWER:

## 3. First-run password setup

The dashboard gets a username/password in both modes. Where does the password come from the first
time?

- **First-load setup page when no password hash exists (Recommended)** — Simon sets his own on
  first boot after update; nothing secret in config.yaml; debug mode pre-seeds `debug` /
  `debug` so tests and Darren's local runs need no manual step (seed happens ONLY when
  `debug_mode` is on).
- **Plaintext password in config.yaml, hashed on load** — simpler, but puts a secret in a file
  the repo rules say must never hold credentials that get committed.

ANSWER:

## 4. Fill realism in the fake bridge

- **Exact fills at the requested/current price, with an explicit error-injection hook
  (Recommended)** — deterministic, e2e-friendly; rejections/timeouts are injected per-scenario to
  test the error paths (the 2026-08-08 review shows those paths matter most).
- **Modelled slippage/spread randomness** — more realistic, but non-deterministic tests and it
  starts becoming a backtester, which is out of scope.

ANSWER:

## 5. Debug DB + flag naming — confirm

Recommendation: config key `debug_mode` (env `FOREX_DEBUG_MODE`), helper `is_debug()`; when on,
the DB path becomes `forex_trader_debug.db` regardless of `account_env`, so demo/live data files
are never touched from a debug session. Say if you'd rather a different name (e.g. `app_mode:
debug|live`) or a different isolation scheme.

ANSWER:

## 6. What runs by default in debug mode?

Engines and auto-execution are DB-flag gated today (`sg_engine_enabled`, `auto_execute_signals`,
…). A fresh debug DB would have them off, and a fresh boot would sit idle.

- **Debug seeds a ready-to-demo state (Recommended)** — engines on, auto-execute on, starting
  balance 1000 — so the first boot visibly trades on fake data within minutes.
- **Debug boots with today's defaults** — truer to production first-run, but you'd flip switches
  in the UI before anything happens (arguably also worth testing once, manually).

ANSWER:

---

## Quick-confirm checklist
- [ ] 1 — licence approach (Simon's sign-off recorded)
- [ ] 2 — scenario format
- [ ] 3 — password first-run flow
- [ ] 4 — fill realism
- [ ] 5 — flag name + debug DB isolation
- [ ] 6 — debug seed state
- [ ] Money flag: only task 020 touches the bridge seam; nothing here changes order placement,
      closing or sizing logic itself.

*Once answered: record each choice in the README's "Decisions locked" table with the date, and
annotate the question above rather than deleting it.*
