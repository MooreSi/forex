# 011 — "Run Analysis" on the Signal Generator panel raises NameError

**Status:** not started — **and it blocks the ai_trade_analysis split**
**Found:** 2026-08-26, by a pyflakes sweep of the whole tree
**Touches money:** no — it is an AI commentary call, not an order path
**Severity:** live, user-facing, silent until clicked

## What happens

`frontend/pages/ai_trade_analysis.py:420`, inside `run_signal_generator_analysis`:

```python
raw = await ai_provider.complete(cfg, _SIGNAL_GEN_SYSTEM, prompt, max_tokens=2048, timeout=timeout)
```

`_SIGNAL_GEN_SYSTEM` is bound nowhere. The file defines `_ANALYSIS_SYSTEM` (L168) and
`_STRATEGY_DPM_SYSTEM` (L257) but never this one, so the call raises `NameError` before
reaching the provider. The panel's **Run Analysis** button does nothing.

## Likely cause

The signal-generator analysis was added by copying the channel and strategy/DPM
analyses, which each have their own system prompt. That third prompt was never written.

## What to do

**Do not invent a prompt.** The other two are carefully worded and their wording shapes
what the model returns. Options, in order of preference:

1. Check whether a system prompt for this exists elsewhere (`backend/src/services/ai/`
   has several `_SYSTEM` constants) and was meant to be imported.
2. If it genuinely was never written, this is a product decision — the panel is asking
   for an analysis nobody specified. Ask before writing one.

Test first either way: `run_signal_generator_analysis` with a fake provider, asserting it
reaches `ai_provider.complete` rather than raising.

## Why this blocks the split

`frontend/pages/ai_trade_analysis.py` is 1,250 lines and over the 800 ceiling, but it
cannot become a package while this stands. `tests/frontend/test_page_packages_are_wired.py`
resolves every global name a page package uses, statically, and is enforced at zero with
no allowlist. A flat module escapes it; a package does not. Splitting the file would turn
this latent bug into a failing gate.

Same situation as [010](010-test-panel-reset-params-nameerror.md). Fix the name, then split.
