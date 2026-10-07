# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal workspace of independent projects around Argentine markets (GGAL, RFX20, dollar futures), not one application. Each top-level directory stands alone; nothing is shared between them except this repo. Windows 11, PowerShell 5.1, Python 3.14. Code, comments, commit messages and reports are in Spanish.

There is no build, lint or test suite. "Verifying" a change means running the script and reading its output.

## Git workflow

**Commit and push after every completed feature or fix — do not wait to be asked.**

- Stage only the relevant files (never `git add -A` blindly)
- Write a short, descriptive commit message that explains the change
- Push to `origin/master` on GitHub (https://github.com/pucciotobias-hub/ClaudeCodeTest) immediately after committing
- For larger tasks, commit at meaningful checkpoints (e.g. after each sub-feature) rather than only at the very end

The goal is that the remote always reflects the latest working state so progress is never lost and any change can be reverted.

The unattended GGAL runs commit and push on their own to the same branch, so the working tree usually holds unrelated uncommitted files: stage by path.

## Projects and how to run them

| Path | What | Run |
|---|---|---|
| `scripts/`, `estudios/ggal/` | Automated GGAL ADR studies (the active project, see below) | `.\scripts\ggal_estudio.ps1 -Turno <apertura\|mediodia\|cierre\|auditoria\|semanal> [-Forzar]` |
| `oficina/` | Three.js scene showing which study agent is working; server on port 8765 | `powershell -File oficina\abrir_oficina.ps1` |
| `tasas/` | Live dashboard of A3 futures (implied dollar rates, rolls, open interest); server on port 8766 | `powershell -File tasas\abrir_tasas.ps1` |
| `flujo/` | Dashboard of estimated buy/sell flow on the GGAL ADR (volume delta, anchored VWAP, relative volume, weekly volume profile) from yfinance 5-minute bars, with a chat that answers through `claude -p` (no tools, run from a temp dir); server on port 8767 | `powershell -File flujo\abrir_flujo.ps1` |
| `app.py`, `modules/` | Streamlit screener (macro, multi-timeframe technicals, fundamentals) on yfinance | `streamlit run app.py` |
| `monitor.py` | GGAL/RFX20 spread z-score monitor over pyRofex. **Signals only: it must never send or cancel orders** (`NOTA_BROKER.md` is the broker homologation request that states this) | `python monitor.py` (needs `.env`, see `.env.example`; deps in `requirements-monitor.txt`) |
| `quant_bot/` | Weekly equity-research PDF sent by Telegram | `python main.py --once` from `quant_bot/` |
| `fresia/` | Rebuilds a company's financial statements PDF with uniform formatting | `python build.py`, `python assertions.py`, `python verify.py` from `fresia/` |
| `cuenta/`, `dashboard/` | Google Apps Script for Sheets against the Cocos/Matriz API; pasted into the Apps Script editor, not run locally | — |

`divergencia_ggal_rfx20.py` is a deprecated v1 of `monitor.py`, kept for reference only.

`fresia/`: every amount in `data.py` is a string and must stay one. Nothing is parsed, recalculated or reformatted; `build.py` aborts if an accounting checkpoint fails and `verify.py` compares each amount against the original PDF.

`scripts/README.md`, `quant_bot/README.md` and `fresia/README.md` hold the detail for each.

## GGAL studies: how the pieces fit

Windows Scheduled Tasks (`scripts/install_ggal_tasks.ps1`) fire `ggal_estudio.ps1` on weekdays. The wrapper makes sure Chrome is up with CDP on port 9222, then runs `claude -p` headless with a **recipe** (`scripts/ggal_*_prompt.md`) prefixed with date, time, turn and output path. The headless Claude drives a live TradingView chart through the `tradingview` MCP server, writes the report and commits it.

- **The recipe is the product.** To change what a study does, edit its `*_prompt.md`, not the wrapper. Recipes carry dated notes explaining why each rule exists; keep that habit when adding one.
- **Turns and outputs:** `apertura`/`mediodia`/`cierre` → `estudios/ggal/<date>-<turn>.md`; `auditoria` (Fridays) → `estudios/ggal/auditorias/<date>.md`; `semanal` (Mondays) → `estudios/ggal/semanal/<date>.json`.
- **Audit proposals are never applied automatically.** The audit proposes recipe changes; the user reads and approves them.
- **One chart, one run.** All turns share the same chart, guarded by the mutex `Local\GgalEstudioChart`. Do not drive the chart from an interactive session while a run is in progress (`logs/ggal_estudio.log` shows `INICIO` without `FIN`).
- **"Done" means committed**, not "file exists": the wrapper checks `git ls-files` to decide whether a retry has work to do.
- **Permissions are an allowlist in the wrapper** (`$allowed` in `ggal_estudio.ps1`). A recipe step that needs a new tool or command fails silently unless it is added there.
- **The wrapper is Windows PowerShell 5.1**, saved as UTF-8 with BOM and CRLF. No `&&`, no ternary, and git's stderr becomes a terminating error under `$ErrorActionPreference = 'Stop'`.
- **Diagnosing a missing or late report:** read `logs/ggal_estudio.log` first. The usual cause is the laptop sleeping at trigger time, not the recipe.

### Weekly report page

The weekly report is read on a published page, https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67, whose source is `scripts/ggal_semanal_pagina.html`. The page renders the JSON embedded in its `<script id="datos">` block and cannot read data from anywhere else.

The Monday run writes the JSON and embeds it with `python scripts/ggal_semanal_incorporar.py <json>`, but **it cannot publish**: the `Artifact` tool does not exist in `claude -p`. The page stays on the previous week until an interactive session republishes it (`Artifact` read of that URL, then publish `scripts/ggal_semanal_pagina.html` with the same `url`).

### TradingView

It is TradingView web in Chrome with the profile `~\tv-cdp-profile`, not the desktop app: the MCP's `tv_launch` does not work here. Relaunch with `scripts\relanzar_chrome_cdp.ps1` (idempotent, only touches the CDP profile's Chrome). Prices always come from the chart feed, never from the web. `data_get_study_values` makes the symbol drift and deletes drawings: do not use it in unattended runs.
