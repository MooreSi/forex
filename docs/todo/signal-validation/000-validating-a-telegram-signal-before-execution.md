# Validating a Telegram signal before execution — design and feasibility

**Status: proposal, 2026-09-18. Nothing built. No code changed.**
Asked: can a second engine validate a Telegram signal (including under IME)
before it executes, to cut losses and improve entry and TP?

**Short answer: yes, and most of it is already built — but the first win is
not an ML gate, and the data says the biggest loss is not in signal
selection at all.** Details below, all figures from the live demo DBs and
`forex_trader.log` read on 2026-09-18.

---

## 1. What already exists (do not rebuild any of this)

The exact machinery being asked for is in the tree, working, and live —
wired to the **Reversal Engine only**:

| Piece | File | State today |
|---|---|---|
| Meta-labeller ("should we act", binary, purged/embargoed CV, uniqueness weighting, refuses to arm below AUC 0.55 / 200 samples) | `reversal_engine/meta_label.py` | `meta_label_gate_enabled = 1` |
| ML gate on live execution | `reversal_engine/ml_engine/` | Blocking live: 5 blocks in the log on 2026-09-18 alone (`predicted_R=-0.096`, `-0.683`, `-0.455`, `-0.027`, `-0.161`) |
| "Does this moment look like one the pros would fire in" | `reversal_engine/pro_model.py` | Trained on **Telegram** signals as positives vs background |
| Corpus of market state at signal time | `pro_corpus_repo.py` → `reversal_engine.db:pro_snapshots` | **9,847 rows** |
| Outcome labeller (walks M1 forward, judges on stated levels) | `reversal_engine/pro_outcome.py` | 1,075 labelled |
| Champion/challenger shadow recording | `reversal_engine/shadow.py` + `shadow_repo` | **700 decisions recorded** |
| Deterministic gates (entry trigger, liquidity map, event tiers, session liquidity, ATR barriers, HTF bias) | `risk/capability_gates.py`, `market/*` | Built and tested; **all off**, and all RE-only |

`capability_gates.py` is imported by `reversal_engine_*`, `cycle_setup`,
`ai_tuner`, the RE panel and `settings_controller`. **Nothing on the
Telegram path imports it.** That is the entire gap.

## 2. What a Telegram signal is actually checked against today

Full-signal path and IME path each keep their own copy of the gate list
(`instant_entry.py:100-175`):

staleness → session → trading schedule → news blackout → HTF bias (off) →
spread → EA template Sig Guard → strategy resolution.

Plus, on the non-IME path only: R:R floor on TP1 and the directional cap
(`governor.check_pre_trade_filters`).

**Under IME the R:R filter is bypassed by construction**
(`governor.rr_filter_bypassed`, second arm) — "take this channel's fill at
market the moment it lands" contradicts an R:R gate measured against the
live price. That was a deliberate 2026-08-06 owner decision, and it means
**IME today executes on direction + template, with no opinion about the
market at all** beyond session/news/spread/bias.

## 3. Is it feasible? Yes — latency is not the constraint

Measured on the real IME execution at 09:22 today (tg_id 21448, VIP):

```
09:22:17,990  MSG buffered
09:22:17,998  IME strategy resolved            (+8 ms)
09:22:18,003  EA handoff check                 (+13 ms)
09:22:18,259  EA order placed @ 4393.63        (+269 ms)
```

**269 ms end to end, of which 256 ms is the broker POST.** The app's own
decision costs 13 ms. The bridge is local (`localhost:9010`, 5-10 ms per
call) and M5/M15/H1/H4 candles are already fetched on the monitor cycle, so
a feature vector is in-process. A deterministic gate costs ~10-50 ms; a
LightGBM `predict` on one row is ~1 ms. That is 4-18% added latency on a
path whose dominant cost is the broker.

Feasibility is not in doubt. **The constraint is the label, not the compute.**

## 4. The data problem, which is the real finding

### 4a. There is not enough of our own outcome data to train on

183 executed Telegram trades, 2026-09-03 → 09-17 (~14 days):

| Source | Trades | Win | Loss | Net $ |
|---|---|---|---|---|
| GOLD DIGGERS INSTITUTIONAL (+ Telegram Auto) | 93 | 34 | 59 | −1,453.79 |
| Gold Diggers VIP (+ Telegram Auto) | 90 | 43 | 47 | −884.57 |

`meta_label.DEFAULT_MIN_SAMPLES = 200`. **A TG meta-labeller trained today
would refuse to arm**, correctly, and an unarmed model has no opinion
rather than a neutral one. That is the existing code being honest, and it
is the right answer to "can ML validate this yet".

### 4b. The labels that DO exist measure the wrong thing

`pro_outcome` judges each signal on **its own stated levels** — filled, then
TP1 before SL. Over 1,075 labelled snapshots (2026-08-04 → 09-18):

```
win      738   avg +0.264 R
loss      84   avg -1.000 R
no_fill  253
```

90% positive class. On gold intraday noise, touching TP1 is close to free —
so this label is nearly constant, and a classifier trained on it learns
almost nothing. Worse, it disagrees with the money:

| What our execution actually did | Trades | Net $ |
|---|---|---|
| Never reached any TP | 95 (52%) | **−4,672.23** |
| Reached TP1 only | 33 | **−104.78** |
| Reached TP2 | 43 | +1,572.02 |
| Reached TP3 | 12 | +866.63 |

**Half of all TG trades never reach a single target, and the ones that reach
TP1 and stop are net negative.** A gate optimised for "will TP1 be touched"
would happily approve the entire losing half.

The label a validator needs is **realised R of our own execution under our
own strategy/template** — after the Logic-Keyword TP/SL overrides, the
template's SL, the partials and DPM. It does not exist in volume yet
because nothing records it as a training row.

### 4c. And the objective splits in two

"Reduce losses" and "improve entry and TP" are different problems, and 4b
says the second is the larger one. 52% never-reach-TP1 and a net-negative
TP1 bucket is a **barrier and exit** problem (`market/barrier_fit.py`,
`market/exit_replay.py` already exist, unused here), not a signal-selection
problem. A perfect validator that only removed losers would still leave the
TP1 bucket losing money.

---

## 5. How I would design it

Four stages. Each is independently valuable and each can stop.

### Stage 0 — Record the decision (no behaviour change, no sign-off needed)

For **every** Telegram signal that reaches the execution decision —
executed, gated or declined — write one row: the feature vector as of that
instant, which gates fired, what was decided, and later the realised R of
our trade if one was opened.

`pro_corpus_repo` already has the snapshot writer and the schema shape;
this is a sibling table keyed on our trade, not on their levels. The
capture must derive from facts the live path **has already computed**
(`shadow.py`'s rule) — never a second market read, which is a different
moment and costs the live path latency.

This is the unblocking step. Nothing else can be honest until ~200 of our
own labelled rows exist, which at current volume is 4-6 weeks.

### Stage 1 — Shadow the gates that already exist (no behaviour change)

Reuse `shadow.py`'s champion/challenger, which already holds 700 RE
decisions. Register TG variants: `entry_trigger` on, `session_liquidity`
on, `event_tier` on, `htf_bias` on, and combinations. Record what each
would have done to each TG signal. Execute nothing differently.

After 2-4 weeks, read off per gate: losses avoided, winners killed, net $.
That is a measurement, not an opinion, and it costs nothing to be wrong.

### Stage 2 — Promote the gates that pay, one at a time

Every one of these already has a settings toggle, a tested implementation
and a UI card. Promotion is a call site plus tests, not new machinery:
import `capability_gates` on the TG path and honour the same four toggles
the RE honours.

Two design rules for the IME path specifically:

- **Pre-computed features only.** Read bias/trigger/liquidity from the
  monitor cycle's cache; never fetch. IME's whole premise is the fill at
  the moment the message lands.
- **No AI call, ever, on the IME path.** `sg_claude_eval_enabled` is a
  seconds-scale round trip. It belongs on the resting/pending path, not here.

One at a time, because a stack of gates promoted together cannot be
attributed when the number moves.

### Stage 3 — A Telegram meta-labeller, only if Stage 0 earns it

A second instance of `meta_label.py` over the Stage 0 corpus. Same
disciplines: purged embargoed folds (TG signals overlap badly — six
concurrent, multi-hour windows), uniqueness weighting, and **refuse to arm**
below 200 samples / 0.55 OOS AUC. Arm it in shadow first; let it vote only
after its shadow record beats the champion on money, not on AUC.

If it converges on blocking most signals, that is not a filter, it is a
verdict on the channel — and `channel_performance` already exists to act on
that more cheaply than any model.

---

## 6. What this does not fix, and what needs the owner

- Nothing here improves TP placement. That is `barrier_fit` / `exit_replay`
  against the 52% that never reach a target, and it is a separate piece of
  work that the same Stage 0 corpus would serve.
- **Every stage past 1 blocks or alters a live order, so it needs owner
  sign-off and a demo session.** Stages 0 and 1 are recording only and do
  not.
- Open question for the owner: should a validator be allowed to *resize*
  rather than only *veto*? A low-confidence signal at 0.3x is a different
  product from a blocked one, and the sizing policy already exists.
