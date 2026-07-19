"""
Reader Logic dialog — per-channel parser configuration, format documentation,
message test panel, and pending unrecognised message review.
"""

import json
import textwrap
from typing import Callable

from nicegui import ui

import forex_trader.config as cfg_module
from forex_trader.core import ai_rule_generator
from forex_trader.core import database as db_module
from forex_trader.core.signal_parser import (
    parse_gold_signal, parse_gd2_signal, parse_gd2_partial, parse_instant_entry,
    SIGNAL_PREFIX,
)

_FORMAT_LABELS = {
    "format_ab": "Format A/B  (Gold Diggers VIP)",
    "gd2":       "GD2  (Gold Diggers 2.0)",
    "auto":      "Auto-detect",
    "none":      "Disabled",
}


async def _push_ai_recovered_sync(action: str, tg_message_id: str, **fields) -> None:
    """Mirror an approve/rule_result/discard action on the AI review queue to
    the paired Local/Remote node, same try-server-then-client pattern as
    ai_rule_generator.py's _broadcast_to_peer_node — see sync/protocol.py's
    MSG_AI_RECOVERED_SIGNAL_SYNC comment for why the queue itself (not just
    the resulting rule) needs to be shared."""
    try:
        from forex_trader.sync import server as sync_server
        srv = sync_server.get_instance()
        if srv is not None:
            await srv.push_own_ai_recovered_signal(action, tg_message_id=tg_message_id, **fields)
            return
    except Exception:
        pass
    try:
        from forex_trader.sync import client as sync_client
        from forex_trader.sync.protocol import CONN_CONNECTED
        cli = sync_client.get_instance()
        if cli.conn_state == CONN_CONNECTED:
            await cli.push_ai_recovered_signal(action, tg_message_id=tg_message_id, **fields)
    except Exception:
        pass

_FORMAT_OPTS = {
    "format_ab": "Format A/B  (Gold Diggers VIP)",
    "gd2":       "GD2  (Gold Diggers 2.0)",
    "auto":      "Auto-detect",
    "none":      "Disabled",
}

_FORMAT_DOCS = {
    "format_ab": {
        "title": "Format A/B — Gold Diggers VIP",
        "description": (
            "Messages must start with the configured signal prefix. "
            "Two sub-formats are supported:\n\n"
            "Format A — Inline direction+range:\n"
            "  'Sell Gold 4520 - 4512'\n\n"
            "Format B — Labelled fields:\n"
            "  'Direction  SELL'\n"
            "  'ENTRY : 4468-4466'"
        ),
        "patterns": [
            ("Direction (Format A)", r"\b(buy|sell)\s+gold\s+([\d.,]+)\s*[-–—]\s*([\d.,]+)"),
            ("Direction (Format B)", r"Direction[\s\xa0]+(BUY|SELL)"),
            ("Entry range (B)",      r"ENTRY[\s\xa0]*:[\s\xa0]*([\d.,]+)[-–—]([\d.,]+)"),
            ("Stop Loss",            r"stop[\s\xa0]*loss[\s\xa0]+([\d.,]+)  OR  SL\s*:\s*([\d.,]+)"),
            ("Take Profits",         r"TP(\d+)[\s\xa0]+([\d.,]+)  OR  TP(\d+)\s*:\s*([\d.,]+)"),
            ("TP Open",              r"TP(\d)\s+Open\s*\(([\d.,/\s]+)\)"),
            ("Currency guard",       r"Currency[\s\xa0]*:[\s\xa0]*([\w]+)"),
        ],
    },
    "gd2": {
        "title": "GD2 — Gold Diggers 2.0",
        "description": (
            "Messages contain 'XAU USD BUY NOW' or 'XAUUSD SELL NOW' followed by "
            "an entry range, SL, and TPs. GD2 sometimes sends the entry range first "
            "and adds SL/TP via a Telegram edit — the app stores these as "
            "'pending_followup' and promotes them when the edit arrives."
        ),
        "patterns": [
            ("Direction",    r"XAU\s*USD\s+(BUY|SELL)\s+NOW"),
            ("Entry range",  r"([\d.,]+)\s*[-–—]\s*([\d.,]+)"),
            ("Stop Loss",    r"(?:🚫\s*)?SL[\s\xa0]*:?[\s\xa0]+([\d.,]+)"),
            ("Take Profits", r"TP(\d+)[\s\xa0]*:?[\s\xa0]+([\d.,]+)"),
        ],
    },
}


def _ts_short(v) -> str:
    if not v:
        return "—"
    from datetime import datetime, timezone
    try:
        dt = datetime.fromtimestamp(float(v)).astimezone()
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return str(v)[:10]


def render_dialog(dialog: ui.dialog) -> None:
    """Render the full READER LOGIC dialog content."""

    with dialog, ui.card().classes(
        "w-full max-w-5xl bg-gray-900 rounded-xl p-0 overflow-hidden"
    ).style("max-height:90vh; display:flex; flex-direction:column;"):

        # ── Header ────────────────────────────────────────────────────────────
        with ui.row().classes(
            "w-full items-center justify-between px-5 py-3 shrink-0"
        ).style("background:#111827; border-bottom:1px solid #374151"):
            ui.label("Reader Logic").classes("text-lg font-bold text-yellow-300")
            ui.button(icon="close", on_click=dialog.close).classes(
                "text-gray-400"
            ).props("flat round dense")

        # ── Tabs ──────────────────────────────────────────────────────────────
        with ui.column().classes("flex-1 overflow-hidden"):
            with ui.tabs().classes("bg-gray-800 shrink-0") as tabs:
                tab_config  = ui.tab("Channel Config",   icon="tune")
                tab_docs    = ui.tab("Format Docs",      icon="article")
                tab_test    = ui.tab("Test Message",     icon="science")
                tab_ai      = ui.tab("AI",               icon="smart_toy")
                tab_history = ui.tab("Resolved History", icon="history")

            with ui.tab_panels(tabs, value=tab_config).classes(
                "flex-1 bg-gray-900 overflow-auto"
            ).style("min-height:0"):
                with ui.tab_panel(tab_config):
                    _render_channel_config()
                with ui.tab_panel(tab_docs):
                    _render_format_docs()
                with ui.tab_panel(tab_test):
                    _render_test_panel()
                with ui.tab_panel(tab_ai):
                    _render_ai_tab()
                with ui.tab_panel(tab_history):
                    _render_resolved_history()


def _render_channel_config() -> None:
    container = ui.column().classes("w-full p-4 gap-3")

    def _build():
        container.clear()
        with container:
            configs = db_module.get_all_channel_parser_configs()
            rules   = db_module.get_channel_learned_rules()

            ui.label("Per-channel parser configuration").classes(
                "text-sm font-semibold text-gray-300"
            )
            ui.label(
                "Each known channel is listed below. Changing the format takes effect "
                "immediately — no restart required."
            ).classes("text-xs text-gray-500")

            if not configs:
                ui.label(
                    "No channels configured yet. Connect Telegram, select a group, "
                    "and the first received message will auto-configure it."
                ).classes("text-xs text-yellow-400 italic mt-2")
            else:
                for cfg in configs:
                    _render_channel_row(cfg, _build)

            ui.separator().classes("my-2")
            ui.label("Add / configure a channel manually").classes(
                "text-xs text-gray-400 font-semibold"
            )
            _render_add_channel_form(_build)

            # Learned rules summary
            if rules:
                ui.separator().classes("my-2")
                ui.label("Learned rules").classes("text-xs text-gray-400 font-semibold")
                for rule in rules:
                    _render_rule_row(rule, _build)

    _build()


def _render_channel_row(cfg: dict, refresh: Callable) -> None:
    channel_name = cfg["channel_name"]
    with ui.card().classes("w-full bg-gray-800 p-3 rounded-lg"):
        with ui.row().classes("w-full items-center gap-3 flex-wrap"):
            ui.label(channel_name).classes(
                "text-sm font-semibold text-white flex-1 min-w-32"
            )
            fmt_sel = ui.select(
                _FORMAT_OPTS,
                value=cfg.get("parser_format", "auto"),
                label="Format",
            ).classes("w-52")
            enabled_sw = ui.switch(
                "Enabled", value=bool(cfg.get("enabled", 1))
            ).classes("shrink-0")
            ime_sw = ui.switch(
                "Instant Entry", value=bool(cfg.get("instant_entry_enabled", 0))
            ).classes("shrink-0")

        prefix_inp = ui.input(
            "Signal prefix (first 40 chars checked)",
            value=cfg.get("signal_prefix", ""),
        ).classes("w-full text-xs")

        notes_inp = ui.input(
            "Notes",
            value=cfg.get("notes", ""),
        ).classes("w-full text-xs")

        save_lbl = ui.label("").classes("text-xs text-green-400")

        def save(ch=channel_name, f=fmt_sel, p=prefix_inp,
                 ime=ime_sw, en=enabled_sw, n=notes_inp, lbl=save_lbl):
            db_module.save_channel_parser_config(
                ch, f.value, p.value, bool(ime.value), bool(en.value), n.value
            )
            lbl.text = "Saved"
            import asyncio
            asyncio.get_event_loop().call_later(2, lambda: setattr(lbl, "text", ""))

        ui.button("Save", icon="save", on_click=save).classes(
            "bg-blue-700 text-white text-xs px-3 py-1 mt-1"
        )


def _render_add_channel_form(refresh: Callable) -> None:
    with ui.row().classes("w-full gap-2 items-end flex-wrap"):
        name_inp = ui.input("Channel name").classes("flex-1 min-w-40")
        fmt_sel  = ui.select(_FORMAT_OPTS, value="auto", label="Format").classes("w-44")
        err_lbl  = ui.label("").classes("text-xs text-red-400 w-full")

    def add():
        name = name_inp.value.strip()
        if not name:
            err_lbl.text = "Channel name required"
            return
        prefix = SIGNAL_PREFIX if fmt_sel.value == "format_ab" else ""
        ime    = fmt_sel.value == "format_ab"
        db_module.save_channel_parser_config(name, fmt_sel.value, prefix, ime, True, "")
        name_inp.value = ""
        err_lbl.text = ""
        refresh()

    ui.button("Add", icon="add", on_click=add).classes(
        "bg-green-700 text-white text-xs px-3 py-1"
    )


def _render_rule_row(rule: dict, refresh: Callable) -> None:
    with ui.row().classes("w-full items-center gap-2 py-1 border-b border-gray-700"):
        ui.label(rule.get("channel_name", "?")[:24]).classes(
            "text-xs text-yellow-300 w-32 shrink-0"
        )
        ui.label(rule.get("action", "ignore")).classes(
            "text-xs text-gray-400 w-20 shrink-0"
        )
        ui.label((rule.get("pattern") or rule.get("notes", ""))[:60]).classes(
            "text-xs text-gray-300 flex-1 truncate"
        )
        ui.label(_ts_short(rule.get("created_at"))).classes(
            "text-xs text-gray-600 w-24 shrink-0"
        )

        def delete(rid=rule["id"]):
            db_module.delete_channel_learned_rule(rid)
            refresh()

        ui.button(icon="delete", on_click=delete).props("flat round dense").classes(
            "text-red-500 text-xs"
        )


def _render_format_docs() -> None:
    with ui.column().classes("w-full p-4 gap-4"):
        ui.label("Signal format reference").classes("text-sm font-semibold text-gray-300")
        ui.label(
            "This documents the regex patterns used for each format. "
            "These are read-only — format selection is done in Channel Config."
        ).classes("text-xs text-gray-500 mb-2")

        for fmt_key, doc in _FORMAT_DOCS.items():
            with ui.expansion(doc["title"], icon="code").classes(
                "w-full bg-gray-800 rounded-lg"
            ):
                with ui.column().classes("w-full p-3 gap-2"):
                    # Description
                    ui.label(doc["description"]).classes(
                        "text-xs text-gray-300 whitespace-pre-wrap"
                    )
                    ui.separator().classes("my-1")

                    # Patterns table
                    with ui.column().classes("w-full gap-1"):
                        for name, pattern in doc["patterns"]:
                            with ui.row().classes(
                                "w-full gap-2 items-start py-1 border-b border-gray-700"
                            ):
                                ui.label(name).classes(
                                    "text-xs text-yellow-300 w-36 shrink-0"
                                )
                                ui.label(pattern).classes(
                                    "text-xs font-mono text-gray-300 flex-1 break-all"
                                )


def _render_test_panel() -> None:
    with ui.column().classes("w-full p-4 gap-3"):
        ui.label("Test a message against a channel's parser").classes(
            "text-sm font-semibold text-gray-300"
        )

        # Channel selector
        configs = db_module.get_all_channel_parser_configs()
        ch_opts = {c["channel_name"]: c["channel_name"] for c in configs}
        ch_opts["__none__"] = "— no channel (try all parsers) —"

        channel_sel = ui.select(
            ch_opts,
            value="__none__",
            label="Channel",
        ).classes("w-full max-w-sm")

        msg_area = ui.textarea(
            "Paste message text here",
            placeholder="Paste a Telegram message to see how it would be parsed...",
        ).classes("w-full").style("min-height:100px")

        result_container = ui.column().classes("w-full gap-2")

        def run_test():
            result_container.clear()
            text    = (msg_area.value or "").strip()
            ch_name = channel_sel.value

            if not text:
                with result_container:
                    ui.label("Paste a message first.").classes("text-xs text-gray-500")
                return

            cfg = None
            if ch_name and ch_name != "__none__":
                cfg = db_module.get_channel_parser_config(ch_name)

            parser_fmt = cfg.get("parser_format", "auto") if cfg else "auto"
            sig_prefix = cfg.get("signal_prefix", "") if cfg else ""

            results: list[dict] = []

            # Instant entry
            inst = parse_instant_entry(text)
            if inst:
                results.append({
                    "parser": "Instant Entry",
                    "matched": True,
                    "data": {"direction": inst[0], "price": inst[1]},
                })

            # Format A/B
            if parser_fmt in ("format_ab", "auto"):
                prefix_ok = not sig_prefix or text.startswith((sig_prefix or SIGNAL_PREFIX)[:40])
                if prefix_ok:
                    parsed = parse_gold_signal(text)
                    results.append({
                        "parser": "Format A/B (parse_gold_signal)",
                        "matched": parsed is not None,
                        "data": parsed,
                        "prefix_ok": prefix_ok,
                    })
                else:
                    results.append({
                        "parser": "Format A/B (parse_gold_signal)",
                        "matched": False,
                        "data": None,
                        "skip_reason": f"Signal prefix not matched — expected: '{(sig_prefix or SIGNAL_PREFIX)[:40]}'",
                    })

            # GD2
            if parser_fmt in ("gd2", "auto"):
                if "XAU" in text.upper():
                    parsed_gd2 = parse_gd2_signal(text)
                    partial    = parse_gd2_partial(text) if not parsed_gd2 else None
                    results.append({
                        "parser": "GD2 (parse_gd2_signal)",
                        "matched": parsed_gd2 is not None,
                        "data": parsed_gd2,
                    })
                    if partial:
                        results.append({
                            "parser": "GD2 Partial (pending_followup)",
                            "matched": True,
                            "data": partial,
                        })
                else:
                    results.append({
                        "parser": "GD2 (parse_gd2_signal)",
                        "matched": False,
                        "data": None,
                        "skip_reason": "No 'XAU' in text — skipped",
                    })

            with result_container:
                for r in results:
                    matched = r["matched"]
                    color   = "bg-green-900" if matched else "bg-gray-800"
                    icon    = "check_circle" if matched else "cancel"
                    icon_cl = "text-green-400" if matched else "text-gray-600"

                    with ui.card().classes(f"w-full {color} p-3 rounded-lg"):
                        with ui.row().classes("items-center gap-2 mb-1"):
                            ui.icon(icon).classes(f"text-lg {icon_cl}")
                            ui.label(r["parser"]).classes(
                                "text-sm font-semibold "
                                + ("text-green-300" if matched else "text-gray-400")
                            )

                        if r.get("skip_reason"):
                            ui.label(r["skip_reason"]).classes("text-xs text-yellow-400")

                        if matched and r.get("data"):
                            data = r["data"]
                            pairs = [(k, v) for k, v in data.items() if v is not None]
                            with ui.row().classes("gap-4 flex-wrap mt-1"):
                                for k, v in pairs:
                                    with ui.column().classes("gap-0"):
                                        ui.label(k).classes("text-xs text-gray-500 uppercase")
                                        ui.label(str(v)).classes(
                                            "text-xs font-mono text-white font-semibold"
                                        )

                if not any(r["matched"] for r in results):
                    with ui.card().classes("w-full bg-yellow-900 p-3 rounded-lg"):
                        ui.label("No parser matched this message.").classes(
                            "text-sm font-semibold text-yellow-300"
                        )
                        ui.label(
                            "This would be flagged as unrecognised for channels with an "
                            "explicit format configured."
                        ).classes("text-xs text-yellow-400")

        ui.button("Run Test", icon="play_arrow", on_click=run_test).classes(
            "bg-blue-700 text-white px-4 py-2"
        )
        result_container


_AI_FIELD_KEYS = (
    "direction", "entry_low", "entry_high", "stop_loss",
    "tp1", "tp2", "tp3", "tp4", "tp5", "tp6", "tp7", "tp8",
)


def _render_ai_tab() -> None:
    container = ui.column().classes("w-full p-4 gap-3")

    def _build():
        container.clear()
        with container:
            rows = db_module.get_ai_recovered_signals(limit=100)

            ui.label("AI-recovered signals").classes(
                "text-sm font-semibold text-gray-300"
            )
            ui.label(
                "Messages the built-in parser didn't recognise, handled instead by the AI "
                "fallback — new entry signals, and follow-up instructions like \"Adjust SL "
                "to 4060\" (already applied to the matching open trade when first seen). "
                "Review each one below — if it's correct, click Approve. Approving generates "
                "a deterministic rule automatically (validated against this exact message "
                "before it's saved), so future messages of this shape are handled without "
                "ever calling an AI again."
            ).classes("text-xs text-gray-500")

            if not rows:
                ui.label("No AI-recovered signals yet.").classes(
                    "text-xs text-gray-500 italic mt-2"
                )
            else:
                pending = sum(1 for r in rows if not r.get("approved"))
                ui.label(f"{len(rows)} total — {pending} awaiting review").classes(
                    "text-xs text-gray-400"
                )
                for row in rows:
                    _render_ai_row(row, _build)

    _build()
    ui.button("Refresh", icon="refresh", on_click=_build).classes(
        "bg-gray-700 text-white text-xs px-3 py-1 mt-2"
    )


def _render_ai_row(row: dict, refresh: Callable) -> None:
    approved       = bool(row.get("approved"))
    rule_generated = bool(row.get("rule_generated"))
    rule_id        = row.get("rule_id")
    row_id         = row["id"]
    is_sl_adjust   = row.get("message_type") == "sl_adjustment"

    border_color = (
        "border-green-700"  if rule_generated else
        "border-yellow-700" if approved else
        "border-orange-700" if is_sl_adjust else
        "border-gray-700"
    )

    with ui.card().classes(
        f"w-full bg-gray-800 p-3 rounded-lg border-l-4 {border_color}"
    ):
        with ui.row().classes("w-full items-start gap-3"):
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(row.get("channel_name", "?")).classes(
                        "text-sm font-semibold text-yellow-300"
                    )
                    if is_sl_adjust:
                        ui.label("SL ADJUSTMENT").classes(
                            "text-xs font-bold text-orange-400"
                        )
                    ui.label(_ts_short(row.get("created_at"))).classes(
                        "text-xs text-gray-500"
                    )
                    conf = row.get("confidence")
                    if conf is not None:
                        ui.label(f"confidence {float(conf):.2f}").classes(
                            "text-xs text-gray-500"
                        )

                if row.get("reasoning"):
                    ui.label(row["reasoning"]).classes(
                        "text-xs text-gray-400 italic mt-1"
                    )

                if is_sl_adjust:
                    with ui.row().classes("gap-4 flex-wrap mt-2"):
                        with ui.column().classes("gap-0"):
                            ui.label("new stop loss").classes(
                                "text-xs text-gray-500 uppercase"
                            )
                            ui.label(str(row.get("new_stop_loss"))).classes(
                                "text-xs font-mono text-white font-semibold"
                            )
                    ui.label(
                        "Already applied to the matching open trade when first "
                        "recognised — approving here only builds the fast-path "
                        "rule for next time."
                    ).classes("text-xs text-orange-300 italic mt-1")
                else:
                    pairs = [(k, row.get(k)) for k in _AI_FIELD_KEYS if row.get(k) is not None]
                    with ui.row().classes("gap-4 flex-wrap mt-2"):
                        for k, v in pairs:
                            with ui.column().classes("gap-0"):
                                ui.label(k).classes("text-xs text-gray-500 uppercase")
                                ui.label(str(v)).classes(
                                    "text-xs font-mono text-white font-semibold"
                                )

                with ui.expansion("Raw message", icon="article").classes("w-full mt-2"):
                    ui.label(row.get("raw_text") or "").classes(
                        "text-xs text-gray-300 whitespace-pre-wrap"
                    )

            action_col = ui.column().classes("gap-1 shrink-0 items-end w-40")

        async def _run_generation(btn):
            btn.disable()
            cfg = cfg_module.load()
            if is_sl_adjust:
                gen_rule_id, note = await ai_rule_generator.generate_sl_adjustment_rule(
                    row["raw_text"], row["channel_name"], row["new_stop_loss"],
                    row["tg_message_id"], cfg,
                )
            else:
                parsed = {k: row.get(k) for k in _AI_FIELD_KEYS}
                gen_rule_id, note = await ai_rule_generator.generate_rule(
                    row["raw_text"], row["channel_name"], parsed,
                    row["tg_message_id"], cfg,
                )
            db_module.mark_ai_recovered_signal_rule_result(row_id, gen_rule_id, note)
            await _push_ai_recovered_sync(
                "rule_result", row["tg_message_id"],
                rule_generated=bool(gen_rule_id), rule_gen_note=note,
            )
            if gen_rule_id:
                ui.notify(
                    f"Rule saved (#{gen_rule_id}) for {row['channel_name']}",
                    type="positive",
                )
            else:
                ui.notify(f"Rule generation failed: {note}", type="negative")
            refresh()

        async def _approve():
            db_module.mark_ai_recovered_signal_approved(row_id)
            await _push_ai_recovered_sync("approved", row["tg_message_id"])
            await _run_generation(approve_btn)

        async def _retry():
            await _run_generation(retry_btn)

        async def _discard():
            db_module.discard_ai_recovered_signal(row_id)
            await _push_ai_recovered_sync("discarded", row["tg_message_id"])
            ui.notify(f"Discarded ({row['channel_name']})", type="info")
            refresh()

        with action_col:
            if rule_generated and rule_id:
                ui.label("Rule saved").classes("text-xs text-green-400 font-semibold")
                ui.label(f"rule #{rule_id}").classes("text-xs text-gray-500")
                ui.button("Discard", icon="delete", on_click=_discard).classes(
                    "bg-gray-700 text-white text-xs px-2 py-1 mt-1"
                )
            elif approved:
                ui.label("Approved").classes("text-xs text-yellow-400 font-semibold")
                if row.get("rule_gen_note"):
                    ui.label(row["rule_gen_note"][:100]).classes(
                        "text-xs text-red-400 text-right"
                    )
                retry_btn = ui.button(
                    "Retry rule gen", icon="refresh", on_click=_retry
                ).classes("bg-orange-700 text-white text-xs px-2 py-1")
                ui.button("Discard", icon="delete", on_click=_discard).classes(
                    "bg-gray-700 text-white text-xs px-2 py-1 mt-1"
                )
            else:
                approve_btn = ui.button(
                    "Approve", icon="check", on_click=_approve
                ).classes("bg-green-700 text-white text-xs px-3 py-1")
                ui.button("Discard", icon="delete", on_click=_discard).classes(
                    "bg-gray-700 text-white text-xs px-2 py-1 mt-1"
                )


def _render_resolved_history() -> None:
    container = ui.column().classes("w-full p-4 gap-2")

    def _build():
        container.clear()
        with container:
            rows = db_module.get_all_unrecognised_messages(limit=100)

            if not rows:
                ui.label("No unrecognised messages recorded yet.").classes(
                    "text-xs text-gray-500 italic"
                )
                return

            ui.label(f"{len(rows)} unrecognised messages (most recent first)").classes(
                "text-xs text-gray-500"
            )

            # Header
            with ui.row().classes(
                "w-full gap-0 px-2 py-1 text-xs text-gray-500 font-semibold "
                "uppercase tracking-wider border-b border-gray-700"
            ):
                ui.label("Time").classes("w-28 shrink-0")
                ui.label("Channel").classes("w-44 shrink-0")
                ui.label("Status").classes("w-24 shrink-0")
                ui.label("Analysis / Resolution").classes("flex-1 min-w-0")

            for row in rows:
                analysis_raw = row.get("claude_analysis") or ""
                analysis: dict = {}
                if analysis_raw:
                    try:
                        analysis = json.loads(analysis_raw)
                    except Exception:
                        pass

                summary   = analysis.get("summary", "—")
                resolution = row.get("resolution") or "—"
                status    = row.get("status", "pending")
                st_color  = (
                    "text-green-400" if status == "resolved" else
                    "text-red-400"   if status == "dismissed" else
                    "text-yellow-400"
                )

                with ui.row().classes(
                    "w-full gap-0 px-2 py-2 text-xs border-b border-gray-700 "
                    "hover:bg-gray-800 items-start"
                ).style("background:transparent"):
                    ui.label(_ts_short(row.get("received_at"))).classes(
                        "w-28 shrink-0 font-mono text-gray-400"
                    )
                    ui.label((row.get("channel_name") or "?")[:30]).classes(
                        "w-44 shrink-0 text-gray-300 truncate"
                    )
                    ui.label(status).classes(f"w-24 shrink-0 {st_color}")
                    with ui.column().classes("flex-1 min-w-0 gap-0"):
                        ui.label(summary[:120]).classes("text-gray-300 break-words")
                        if resolution != "—":
                            ui.label(f"Resolution: {resolution}").classes("text-gray-500")
                        # Raw text preview
                        raw = (row.get("raw_text") or "")[:120]
                        ui.label(raw).classes("text-gray-600 italic text-xs break-words mt-1")

    _build()
    ui.button("Refresh", icon="refresh", on_click=_build).classes(
        "bg-gray-700 text-white text-xs px-3 py-1 mt-2"
    )
