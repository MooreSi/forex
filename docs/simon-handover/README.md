# For Simon — the handover pack

Hi Simon. This folder is for you. Everything in it is written in plain
English — no programming knowledge needed. Darren has spent the last while
getting your trading app into shape to hand back to you, and this folder is
the record of what was done, what we need from you, and what happens next.

## What has been done (in plain English)

**The app now explains itself.** The first time it opens, it shows a "Start
Here" checklist — is the licence active, is MetaTrader connected, is your
risk set — with a button on each unfinished item that takes you to the right
place. There's a "?" help button on every screen, every tab has a plain
description, and the About page is now organised into "set up once" and
"every day".

**It can run in a safe practice mode.** The whole app can now start with no
trading account, no Telegram, no internet — it generates pretend prices and
pretend signals so you can watch it find a trade, open it, manage it and
close it, with no possibility of real money moving. A big amber "DEBUG MODE"
banner makes it impossible to confuse with the real thing. One small switch
that connects this practice mode into the app is deliberately left for you
to approve (see "What we need from you").

**The plumbing is sturdier.** Database upgrades now happen in careful
numbered steps that have been tested against old copies of the data, daily
backups are taken automatically, and the dashboard only accepts connections
from the computer it runs on. The automated tests that guard the app were
audited — tests that looked like protection but actually checked nothing
were removed and are now impossible to reintroduce.

**The safety brake was reviewed.** The "circuit breaker" (which pauses new
trades after a run of losses) is well designed — it survives restarts, works
across both machines, and never closes your open positions. Two improvements
were identified and are waiting for your go-ahead: it currently ships
switched OFF by default, and one failure it should shout about it currently
only whispers.

**Nothing about how it trades has changed.** Every change above is about
usability, plumbing and testing. The rules of this project say that anything
touching real orders — opening, closing, sizing — needs *you* to approve it
and watch it demonstrated. That work is prepared and waiting (see below).

## What we need from you — step by step

**Step 1 — Answer the questions (about 30 minutes, no computer skills
needed).** Open [session-agenda.md](session-agenda.md) and work down Part A.
Each row links to one of the numbered files in this folder; open the file,
read "The question" and the recommendation, and type your answer on the
**Answer:** line (in any text editor — even Notepad). *"Confirm — keep what
you chose"* is a complete answer for every one of them. When all six are
answered, tell Darren.

**Step 2 — The demo session on your machine (with Darren).** After your
answers, the money-safety work gets built, and you watch each protection
demonstrated on your **demo** account (never the live one) before it ships —
one position instead of two on a timeout, no phantom closes, the safety
brake on by default. The agenda's Part B lists exactly what you'll watch.

## How to run the app

**The safe way first — practice mode (no keys, no account, no internet):**
open a terminal in the app folder and run:

```
set FOREX_DEBUG_MODE=1
python run.py
```

then open **http://localhost:8890** in your browser and log in with
username `debug`, password `debug`. Everything you see is simulated — the
amber banner across the top confirms it. This is the best way to explore
without any risk at all.

**The real app:**

```
python run.py
```

then open **http://localhost:8888**. The first thing to do there is follow
the **Start Here** checklist that pops up — it checks each requirement
(licence, MetaTrader connected, risk set) and its "Fix this →" buttons take
you to the right screen for each one.

**Where your keys and accounts go** — all inside the app, under
**Settings**:

- **MetaTrader:** Settings → *MT5 / Bridge* — your account login, password
  and server (demo and live are entered separately; the app starts in demo).
- **Telegram signals** (optional): Settings → *Telegram Alerts*, plus the
  Parsing tab to connect channels. Creating the Telegram API key is a
  one-time step — the app's **About → Setup Instructions** walks it through
  click by click.
- **AI commentary** (optional): Settings → *AI* — your Anthropic key.
- **Email reports** (optional): Settings → *Email Reports*.

Nothing needs editing in files — every key is entered through those screens,
and the **? Help button** (top right, any screen) opens a guide that links
to all of this. If anything is unclear, that's a bug in our docs — tell
Darren and we fix the doc, not you.

## What's in this folder

| File | What it is |
|---|---|
| [session-agenda.md](session-agenda.md) | The agenda for your two sittings — decisions, then demos |
| [questions.md](questions.md) | The decision queue: how it works and the full list |
| `001, 002, 004, 005, 007` | Your five decisions, one file each — options spelled out, you write on the **ANSWER:** lines |
| [readiness-checklist.md](readiness-checklist.md) | The honest "is it ready?" scorecard — what's green, what's not, and why |
| [future-roadmap.md](future-roadmap.md) | Ideas for after the handover — not commitments, a menu |

## The one-line summary

The app is easier to use, safer to change, provably testable, and can be
demonstrated end-to-end without risking a penny — and the only work left
before you can trust it live is the work that was always going to need you
in the room.
