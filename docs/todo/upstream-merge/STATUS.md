# Upstream merge — where it actually stands

_2026-08-25. Read this before trusting the branch._

## The honest number

| | Pre-merge (`a27df81`) | After the merge |
|---|---|---|
| passed | 2,076 | **2,941** |
| failed | **1** | **100** |
| errors | 0 | 7 |
| collected | 2,077 | 3,048 |

Measured on macOS with the same command on both trees
(`pytest tests/ -q`), the pre-merge tree checked out in its own worktree.
The single pre-merge failure is `test_pyproject_metadata.py::
test_build_backend_is_importable`, an environment artefact, and it still fails
after the merge.

**So the merge is structurally complete but NOT green.** Every conflict is
resolved, nothing carries a conflict marker, the whole tree parses, 25 key
modules including `backend.src.app`, `backend.src.runtime` and `frontend.app`
import cleanly, the 192-statement migration chain applies to a fresh
legacy-shape database, and pyflakes reports no undefined names beyond the
pre-merge baseline of six. But ~100 tests fail that did not fail before, and
that gap is real work, not noise.

`FAILING-TESTS.txt` in this directory is the exact list.

## What the failures are

Roughly, and each needs confirming individually rather than assuming:

- **Relocated subjects.** Upstream tests reach for methods on the engine
  (`SimulationEngine._cmd_*`, `_orb_auto_execute`) that the refactor moved into
  services. The behaviour is covered by the refactor's own surface tests; the
  upstream tests need re-pointing at the new home. `test_orb_report_*` and
  `test_monitor_loop_characterization` are mostly this.
- **Deleted subjects.** `test_news_debug.py` patches `_from_mt5` /
  `_from_finnhub` / `_from_forexfactory`, all deleted upstream (two were dead,
  the third held the field-name bug that stopped the blackout ever firing).
- **Structural gates.** `test_import_contracts`, `test_structure_gates`,
  `test_orphan_modules`, `test_fixture_dedup`, `test_layout` fail because
  upstream's month of additions breach the shrink-only ratchets and the
  frontend/db boundary. This is the documented, accepted consequence of landing
  the merge before decomposing — see DECISIONS.md. **The baselines were not
  lowered.**
- **Genuine integration gaps.** `test_grid_leg_profit_sync`,
  `test_pending_expiry_windows`, `test_market_week`, `test_autostart` and
  friends need reading properly. These are the ones that could hide a real
  defect, and they are where the next session should start.

## What this means for the demo session

Nothing here goes near `main`, and nothing here is demo-ready. The Part B
sign-off demos need a green suite first: a failing suite cannot tell you whether
the port changed behaviour, and "it imports and most tests pass" is exactly the
kind of green-looking evidence this project's rules were written against.

## Fixed while getting here, worth knowing

Three regressions this merge introduced and then closed, each found by running
the suite rather than by reading the diff:

1. `tests/conftest.py` lost `fresh_db` / `make_engine` (539 errors) — the two
   sides' conftests were unioned instead.
2. A stale `licence.keygen` import survived in `remote/server.py`'s
   `approve_registration` (18 failures).
3. `test_bot_commands_readonly_characterization.py` was restored on a reading of
   the commit history that running it disproved — see DECISIONS.md.
