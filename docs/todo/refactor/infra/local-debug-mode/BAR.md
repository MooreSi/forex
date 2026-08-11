# Screen Bar — Dashboard Login + Debug Banner

**Surface:** Page (login) + persistent Section (debug banner)
**File:** `frontend/app.py` (banner: above the header row at `:893`; login: new page module — see
task 060 for the split, since `frontend/app.py` is already over the 800-line gate)
**Opens from:** login — any unauthenticated request to `/`; banner — always visible on every tab
while `debug_mode` is on
**Reads from:** login — new `auth_controller` (verify against the scrypt hash); banner —
`config.is_debug()` only (no data)
**Touches money:** no — but the banner exists precisely because everything money-shaped on screen
is fake while it shows
**Status:** draft

> **This is a draft an agent wrote. It is not a bar until you edit it.**
> Rewrite the parts that are wrong, delete the parts you do not want, then change `Status:` to
> `agreed`.

## Layout

```
Login page (unauthenticated):
┌──────────────────────────────────────┐
│            FOREX Trader              │
│   Username  [______________]         │
│   Password  [______________]         │
│            [ Sign in ]               │
│   (error line, only after a failure) │
└──────────────────────────────────────┘

Every page, debug mode on (banner above the existing 54px ticker header):
┌──────────────────────────────────────────────────────────────┐
│ ⚠ DEBUG MODE — simulated data, no real orders    [details]   │  ← amber, full width
├──────────────────────────────────────────────────────────────┤
│ (existing ticker strip: logo · BID/ASK · spread · MT5 BAL …) │
└──────────────────────────────────────────────────────────────┘
```

## Anatomy

| # | Part | Component | Holds | Shown when |
|---|---|---|---|---|
| 1 | Login card | `NEW: frontend/pages/login` | username + password inputs, sign-in button, error line | no valid session |
| 2 | First-run setup card | `NEW: frontend/pages/login` (variant) | choose username + password (twice), save button | no password hash exists yet |
| 3 | Debug banner strip | `NEW: frontend/components/debug_banner` | warning text + optional "details" popover (which fakes are active, scenario name) | `is_debug()` true |
| 4 | Logout entry | inline (existing power dialog at `frontend/app.py:743`) | "Sign out" action | authenticated |

## States

| State | Trigger | Renders |
|---|---|---|
| Loading | never — login is static, banner reads a local flag | cannot happen |
| Empty | no password hash on disk | first-run setup card (part 2) instead of login |
| Error | wrong username/password | login card + "Wrong username or password." (no hint which) |
| Disabled | 5 failed attempts in a row *(starting value)* | sign-in button disabled 60s with a countdown |
| Stale | session older than 7 days *(starting value)* | redirected back to login |

## Copy

| Where | Text |
|---|---|
| Banner | `DEBUG MODE — simulated data, no real orders` |
| Banner tooltip | `Every price, balance and order on this screen is simulated. Nothing reaches a broker.` |
| Login title | `FOREX Trader` |
| Login button | `Sign in` |
| Login error | `Wrong username or password.` |
| First-run title | `Set a dashboard password` |
| First-run note | `This protects the dashboard on port 8888. You'll need it every time you open the app.` |
| Sign out | `Sign out` |

## Rules

- The banner is not dismissible and renders on every page/tab while debug mode is on — including
  the login page itself.
- The banner must come from `is_debug()` alone — never inferred from data, so it can never
  wrongly show (or wrongly hide) based on what the fakes return.
- Login gates every route NiceGUI serves, not just `/` (middleware, not per-page checks).
- No credential ever appears in a log line or a URL.

## Out of scope

- Password reset flows (delete the hash file to reset — documented in task 090's help text).
- Multiple users, roles, HTTPS — see pack "Out of scope".
