# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

Open `tictactoe.html` directly in a browser — no build step, no server, no dependencies. All code is self-contained in the single file.

## Architecture

Everything lives in `tictactoe.html` as a single-file app with three co-located sections:

- **`<style>`** — all CSS, using a dark navy/red/teal color palette (`#1a1a2e` background, `#e94560` for X, `#a8dadc` for O)
- **`<body>`** — static HTML structure: scoreboard (`#scores`), status line (`#status`), 3×3 grid (`#board` with `.cell[data-i]` elements), reset button
- **`<script>`** — all game logic in plain vanilla JS (no frameworks)

### Game logic

- `WINS` — hardcoded array of the 8 winning index combinations
- `board` — flat 9-element array mirroring the grid cells by `data-i` index
- `current` — active player (`'X'` or `'O'`)
- `over` — boolean flag that blocks moves after game ends
- `scores` — `{X, O, D}` object persisted across rounds (not persisted across page reloads)
- `init()` resets board state and DOM without touching scores
- Click handling is delegated to `#board` via a single event listener using `e.target.closest('.cell')`

## Git workflow

**Commit and push after every completed feature or fix — do not wait to be asked.**

- Stage only the relevant files (never `git add -A` blindly)
- Write a short, descriptive commit message that explains the change
- Push to `origin/master` on GitHub (https://github.com/pucciotobias-hub/ClaudeCodeTest) immediately after committing
- For larger tasks, commit at meaningful checkpoints (e.g. after each sub-feature) rather than only at the very end

The goal is that the remote always reflects the latest working state so progress is never lost and any change can be reverted.
