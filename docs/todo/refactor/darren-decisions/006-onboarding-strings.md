# 006 — Onboarding wording: checklist rows, tab subtitles, empty-state prompts

**Decision:** PROVISIONAL — the review's proposed wording was adopted verbatim-in-spirit so
phase 1 could ship; Darren reviews the strings in the running app and edits the data files.

**Who decides:** Darren (usability wording — no trading policy involved).

## The question

Stage 2 phase 1 (usability) required user-facing strings that the task files said Darren should
confirm before building: the Start Here checklist rows, the ten tab subtitles, the empty-state
prompts, and the "Set up once / Every day" About grouping. This session was run with the
instruction to complete all of stage 2, so the strings were written from the
2026-08-11 onboarding review's concrete proposals rather than waiting.

## What was chosen (and where to edit it)

| Surface | Chosen wording lives in |
|---|---|
| Start Here checklist rows (6: licence, MT5, algo, risk, telegram-optional, demo) | `frontend/components/start_here.py` (`_STEPS`) |
| Tab subtitles (all 10 tabs, rendered as tooltips; names NOT changed) | `frontend/components/tab_labels.py` (`TAB_SUBTITLES`) |
| Empty-state prompts (TG signals, closed trades, day detail) | `frontend/components/empty_state.py` (`EMPTY_STATES`) |
| Daily routine 3-step loop (Getting Started + About share one copy) | `frontend/components/getting_started.py` (`DAILY_ROUTINE`) |
| About grouping (Set up once / Every day) | `frontend/components/about_home.py` |

Also chosen: tabs keep their existing names (subtitles-as-tooltips instead of renames), because
handlers compare against tab names and a rename is a behaviour risk for zero extra clarity.
"Fix this →" jumps land on the right top-level tab; the exact Settings sub-tab is named in the
row's hint text (deep-linking into settings.py's local tab objects was deliberately not built —
it needs the phase-4 settings split first).

## What changes if the answer differs

All of these are data-only edits in the files above — no logic, no test rewrites except the
copy-pinning assertions in `tests/frontend/test_*` naming the same strings. Nothing trades
differently under any wording.
