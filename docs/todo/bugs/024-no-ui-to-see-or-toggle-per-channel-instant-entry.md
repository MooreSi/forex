# 024 — No UI to see or toggle a channel's own Immediate Market Entry flag

**Status:** **FIXED 2026-09-05**, test-first. The switch is on the Channels
Active card. **No demo session needed for the change itself** — no order,
close or sizing code is touched — but see *What shipped* at the bottom for the
one thing that is still the owner's, and for the immediate action below, which
this fix deliberately does not take.
**Originally:** confirmed live, 2026-09-03. Root cause of a related report (023's
sibling investigation): GOLD DIGGERS INSTITUTIONAL matched the "PREPARE FOR A
BUY" lexicon trigger correctly but never executed, because its own
`instant_entry_enabled` flag is off in the database — and there is currently
no way to see or change that from the app.
**Found:** live DB query (read-only), `forex_trader_demo.db`, while
investigating why a matched BUY-orders lexicon phrase produced no order.
**Touches money:** indirectly — this flag gates whether Instant Market Entry
places a real order for a channel at all, but the fix itself is a UI
read/write of an existing flag through the existing save path, not new order
logic.
**Severity:** a channel's IME behaviour is silently wrong (on or off) with no
way to confirm or correct it except a direct database query.

## What was found

Two gates control whether a matched bare-direction/lexicon trigger becomes a
real market order (`scan_messages.py:233`):

```python
if bool(rs.get("immediate_market_entry", 0)) and ime_enabled:
```

- **Global** — `vantage_risk_settings.immediate_market_entry`, toggled from
  the Parsing page ("Immediate Market Buy/Sell", `_keywords.py:40-44`).
  Confirmed **ON** in the live demo DB.
- **Per-channel** — `channel_parser_config.instant_entry_enabled`. Confirmed
  in the live demo DB:

  | channel | format | instant_entry_enabled |
  |---|---|---|
  | Gold Diggers VIP | format_ab | 1 |
  | GOLD DIGGERS INSTITUTIONAL | gd2 | **0** |
  | Gold Diggers Scalping | gd2 | 1 |

So "PREPARE FOR A BUY" from GD Institutional matched the lexicon exactly as
designed, the global gate was open, and the per-channel gate was closed —
correctly falling through to the silent bare-direction skip in
`scan_parse_classify.py:170-188`. Nothing is broken in the matching or
execution logic; the channel's own setting is simply off, most likely a
leftover from when this channel was still "GOLD DIGGERS 2.0 ⚡️" — channel
config is keyed by `channel_name` string
(`services/channels/parser_repo.py:33`), not the underlying Telegram
`group_id`, so the 2026-07-24 rename to "GOLD DIGGERS INSTITUTIONAL"
(`tests/reversal_engine/test_signal_generator.py:1-22`) would have produced a
config row independent of whatever the old name's row held.

## The actual gap: no UI touches this flag

`instant_entry_enabled` appears in exactly two frontend call sites, both in
`frontend/pages/telegram/_feed.py`, and both only **echo it back unchanged**:

- `_feed.py:72` — the "Channels Active" enable/disable switch
  (`_on_toggle`, 40-82) rebuilds the full `save_channel_parser_config(...)`
  call to persist the *enabled* switch, but passes
  `existing.get("instant_entry_enabled", 0)` straight through. That grid has
  no second switch for IME at all.
- `_feed.py:269` — resolving an "unrecognised message" into `format_ab`/`gd2`
  does the same: rewrites `parser_format`, echoes `instant_entry_enabled`
  unchanged.

So the only way this flag is ever set today is whatever a channel's
auto-bootstrap wrote the first time the channel was seen
(`scan_messages.py:149-163`), and the only way to change it afterwards is a
direct database edit. That's a real usability gap independent of this
specific incident — any channel's IME setting could be silently wrong,
indefinitely, with nothing in the app surfacing it.

## What to change

Add a second switch to the existing "Channels Active" card in
`_feed.py:57-82`, next to the current enable/disable switch, reusing the same
`save_channel_parser_config(...)` call already there — just pass the new
switch's value instead of echoing `existing.get("instant_entry_enabled", 0)`.

```python
ime_sw = ui.switch(
    "Instant Entry", value=bool(cfg.get("instant_entry_enabled", 0)),
).classes("text-xs")

def _on_ime_toggle(e, ch=channel_name, existing=cfg):
    tg_controller.save_channel_parser_config(
        ch,
        existing.get("parser_format", "auto"),
        existing.get("signal_prefix", ""),
        bool(e.value),
        bool(existing.get("enabled", 1)),
        existing.get("notes", ""),
    )
    ui.notify(
        f"{ch} instant entry {'enabled' if e.value else 'disabled'}",
        type="positive" if e.value else "warning",
    )
ime_sw.on_value_change(_on_ime_toggle)
```

No backend change needed — `save_channel_parser_config` and
`get_channel_parser_config` already accept/return this field
(`services/channels/parser_repo.py`); this is purely wiring an existing
read/write path into a visible control, the same shape as the `enabled`
switch already on that card.

## What not to change

- Don't touch `scan_messages.py:233`'s gating logic, the lexicon matcher, or
  the bare-direction fallback — all three are working as designed per this
  investigation.
- Don't add a global default-on migration for existing channels. Leave every
  channel's current stored value as-is; this only adds visibility and manual
  control, not a behaviour change to any channel that isn't explicitly
  toggled.

## Test plan

This is a thin UI wiring change over an already-tested backend path
(`save_channel_parser_config`/`get_channel_parser_config` have their own
coverage). Add one frontend-level test asserting the new switch's
`on_value_change` handler calls `save_channel_parser_config` with the new
switch value in the `instant_entry_enabled` position and the *existing*
`enabled` value unchanged — mirroring how the existing `_on_toggle` handler
would be tested, mocking `tg_controller.save_channel_parser_config`. No
broker, no `open_trade`, no fake needed beyond the existing controller mock
pattern used elsewhere in `frontend/pages/telegram/`.

## Verification

```bash
pytest tests/ -k "channel_parser_config or telegram_feed" -q
python -m tools.checks all
```

No close-path or order-placement code is touched, so no demo session is
required for this specific change — but flipping the switch for a real
channel afterwards does start real market entries for that channel per the
existing IME behaviour, so treat the *toggle itself*, once shipped, with the
same care as any other IME on/off decision.

## Immediate action, separate from the code fix

Until the UI ships, GOLD DIGGERS INSTITUTIONAL's `instant_entry_enabled`
stays at whatever value it currently holds. Confirm with the owner whether
that channel is *supposed* to have Instant Market Entry on before flipping it
by hand — this doc only explains why nothing fired, it does not decide
whether it should.

---

## What shipped, 2026-09-05

Built as written above, with three departures worth naming.

**The save goes through a helper, not a second copy of the call.**
`save_channel_parser_config` takes six POSITIONAL arguments, and the two this
card owns — `instant_entry_enabled` and `enabled` — are adjacent booleans. A
second hand-written call site is an invitation to pass them the wrong way
round, which would disable a channel while reporting that instant entry had
changed: it type-checks, it runs, and it does the opposite of what was asked.
So both handlers call `_feed._save_channel_flags(channel, existing, *,
instant_entry, enabled)`, which is **keyword-only** for exactly that reason and
carries the rest of the row through unchanged.

**The notify colours are inverted relative to the enable switch.** Turning
instant entry ON is `warning`, not `positive`. Switching it on arms real market
entry from bare directions for that channel, so the confirmation should read as
a caution. Turning it off is the safe direction.

**Tests are a detached render of the real section, not a source grep.**
`tests/frontend/conftest.py`'s harness stubs a reader that reports no slots, so
this card draws its "No channels loaded yet" empty state there and no switch
exists to find. The tests render `_render_channels_active_section` directly
into a `ui.card()`, walk the element tree, and fire the switch's real handler —
the same code path, with the slots the card is about. They assert the **exact**
six-argument call rather than that a save happened.

Eight tests in `tests/frontend/test_channel_instant_entry_toggle.py`, all
watched failing first (seven of them; the eighth guards the existing enable
switch and was green from the start, which is the point of it). Six mutants,
all killed:

| Mutant | Killed by |
|---|---|
| the two adjacent booleans swapped in the helper | 3 tests |
| the switch always renders off | 2 |
| the handler writes the stored value, not the new one | 3 |
| the closure loses its per-channel binding | 1 |
| the enable switch stops preserving the flag | 1 |
| the switch is never wired to its handler | 4 |

`python -m tools.checks all`: 11/11.

### Still not done, deliberately

The *Immediate action* above stands and this change does not perform it. GOLD
DIGGERS INSTITUTIONAL's `instant_entry_enabled` is untouched, and no migration
defaults any channel on or off — exactly as *What not to change* requires. The
switch now makes that value visible and correctable; whether that channel
*should* have instant entry on is the owner's call, and flipping it starts real
market entries.
