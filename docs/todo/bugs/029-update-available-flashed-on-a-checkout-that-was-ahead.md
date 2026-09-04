# 029 — "Update Available" flashed on a checkout that was AHEAD of origin

**Status:** fixed 2026-09-04, test-first, all checks green.
**Found:** live, 2026-09-04, reported by the owner: the badge flashes, and
clicking it shows a popup with nothing in it.
**Touches money:** no.
**Severity:** a permanently flashing badge that, if pressed, would have
replaced the working tree with an OLDER commit.

## What was seen

The header badge flashing "Update Available". Clicking it opened the popup
with no summary and no commit list — just *"The commit list for this update
could not be read."*

## Root cause

`check_for_update` decided availability with `local_sha != remote_sha`. That
is equally true in three different situations: the checkout is behind origin
(a real update), **ahead** of it (an unpushed local commit), or diverged.

Reproduced directly in the development checkout, which had one unpushed
commit at the time:

```
available: True
local : 502e023f29cbe502a0ef217351deaf2e83921d11
remote: 334fcd4aaecab06e4ed7ba38097dfb04b7243071
commits: []
```

`git log <local>..<remote>` lists what origin has that we do not, so in the
ahead direction it is empty. That empty list is the whole popup: no commits
to list, and `changes_digest` returns `""`, so `summarise_changes` gives up
with "no commit details available" and the fallback text is all that is left.

The AI summary was never broken. The badge was lying about there being
anything to summarise.

## What changed

Availability is now `rc != 0 or bool(commits)`.

The two empty-list cases are not the same fact and must not be collapsed:

- a log that **failed** (`rc != 0`) means we could not tell, and still assumes
  an update — `test_an_unreadable_log_still_reports_the_update` has pinned
  that since the function was first covered ("knowing an update exists matters
  more than being able to list it"), and it was not touched;
- a log that succeeded and returned nothing means the range really is empty
  and there is nothing to pull.

`--no-merges` cannot hide a real update here: a merge brings the side branch's
own non-merge commits into the range with it.

## Verification

`tests/positions/test_app_update.py::TestOnlyBeingBEHINDOriginIsAnUpdate` —
red first on the two behavioural assertions, with the control
(`test_a_REAL_update_is_still_offered`) passing, without which a guard that
answered "no update" to everything would have passed the whole class and
silently stopped the app updating for ever. Also pins the invariant that the
badge and the popup can never disagree.

The file moved from `tests/core/` to `tests/positions/` in the same change, as
40-testing.md requires when a legacy test is touched.

`python -m tools.checks all` green (11 checks).

## Not done

The live AI summary call was not exercised end to end — it bills the owner's
configured provider (deepseek) and sends the commit log to it. Everything up
to that call is verified: the provider reads as configured, and
`changes_digest` produced 6,915 characters for a real range.
