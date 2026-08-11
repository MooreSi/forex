# Core AI Signal Fallback Migration

Extracts `SimulationEngine._try_ai_signal_fallback`, `_push_ai_recovered_created`,
`_apply_sl_adjustment`, `_queue_unrecognised`, `_analyse_unrecognised_message`
(core/engine.py) into a standalone module. Second pack of the broader
"finish everything off" push through the remaining `core/engine.py` subsystems,
continuing from `core-dpm-handler-migration`.

Three related but distinct flows, all triggered when the deterministic Telegram
message parser fails to recognise a message:

  1. **AI signal fallback** (`_try_ai_signal_fallback`) -- one AI call
     (`ai_signal_extractor.classify_message`) either recovers a missed entry
     signal or recognises an "Adjust SL to X" follow-up instruction. Gated to
     the active-trader node, deduplicated per (tg_id, text), with a cheap
     non-XAUUSD pre-check before the AI call. `_push_ai_recovered_created`
     mirrors a newly-recovered row to the paired Local/Remote node (best-effort,
     safely no-ops in a test environment with no sync server/client running).
  2. **SL adjustment application** (`_apply_sl_adjustment`) -- applies a
     recognised SL-adjustment instruction to whichever open trade the
     originating channel most recently produced. Deduplicated per tg_id.
  3. **Unrecognised-message analysis** (`_queue_unrecognised` /
     `_analyse_unrecognised_message`) -- a separate, simpler AI classification
     path (`claude_ai.classify_unknown_message`) purely for surfacing a
     human-readable summary in the UI; doesn't feed back into signal creation.

`ai_signal_extractor.classify_message` and `claude_ai.classify_unknown_message`
are real AI-provider calls -- faked in tests via `unittest.mock.patch.object`,
same treatment as `dpm_engine.compute_adaptive_params` in the DPM handler pack:
an external, already-stable collaborator, out of scope for this extraction.

See `PROGRESS.md` for task status.
