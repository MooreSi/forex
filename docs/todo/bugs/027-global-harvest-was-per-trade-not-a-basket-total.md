# 027 — Global Harvest was per trade, so a $75 target never fired on $90 of profit

**Status:** fixed 2026-09-04 in the EA (v1.06). **NOT COMPILED AND NOT
DEMOED** — this closes real positions. Needs `tools/deploy_ea.sh`, F7, and a
demo session.
**Found:** live, 2026-09-04, reported by the owner: "the global harvest on
the gui is not working ... it also says per trade and this should be the sum
of all trades".
**Touches money:** yes — it closes positions.
**Severity:** the feature never did what the card described, and the panel
line was the only thing on screen that said so.

## What was seen

Trading > Global Parameters had Harvest ON at $75. The chart panel read
`GLOBAL HARVEST: ON at $75.00 profit per trade`, and nothing was ever
harvested.

## Root cause

Not a delivery failure — `push_global_config` reaches the EA on every "hello"
and every save, and the panel proves it arrived. The semantics were wrong:
`CheckGlobalHarvest` closed each position whose OWN floating profit reached
the threshold. A basket of six trades at $15 each is $90 of open profit that
a $75 per-trade harvest never touches.

## What changed

`CheckGlobalHarvest` now sums every open position on the symbol and closes
them ALL when the total reaches the threshold — the account-wide mirror of the
template-level `basket_harvest_threshold`
(`core_equity_protect.check_basket_harvest`), and of `equity_protect` in the
loss direction.

**Deliberate consequence, stated plainly:** closing the basket closes every
position on the symbol, including any individually in loss. That is what
banking a combined total means; closing only the winners leaves the losers
running and books less than the threshold that just triggered.

The panel now shows the live total against the target
(`$12.40 / $75.00 combined (6)`) from the same `GlobalHarvestFloating()` the
check uses, so the display cannot drift from the trigger. The Global
Parameters card's description was rewritten to match.

## Also in this change

`EA_VERSION` 1.05 → 1.06, `#property version` with it, and a new
`EA_VERSION_DATE` sent in "hello" and printed on connect. `__DATETIME__` only
says when the `.ex5` was compiled — compiling a three-week-old file stamps it
today, which is exactly how the day at the top of `tools/deploy_ea.sh` was
lost. The rule that every EA change bumps both is now in the broker domain
README and beside the `#define`.

The version handshake will report the running EA as stale until it is
recompiled. That is the mechanism working, not a fault.

## Sign-off needed

Demo session. This closes positions on a rule that did not previously fire at
all, so the first live trigger is the first time the behaviour has ever run.
