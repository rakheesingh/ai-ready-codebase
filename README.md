# airead — make your codebase AI-ready, one function at a time

`airead` scores every function in a Python project on **AI-readability** and
walks you through fixing the worst ones one at a time. The goal: code that an
LLM (Cursor, Copilot, agents) can reason about from the function signature
plus a few lines of context — no spelunking required.

## What "AI-ready" means here

A function is AI-ready when it scores well on these dimensions:

| Dimension            | What it checks                                                             |
| -------------------- | -------------------------------------------------------------------------- |
| Naming clarity       | Function and parameter names reveal intent (no `data`, `tmp`, `x`, `do_*`) |
| Single responsibility| Function is short, low complexity, does one thing                          |
| Side-effect honesty  | The verb in the name matches the behavior (`get_*` doesn't mutate, etc.)   |
| Local reasoning      | Does not rely on hidden globals, in-body imports, or closure state         |

Each dimension is scored 0–2, so a function gets 0–8 overall.

## How it works

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   STATIC ANALYZERS      │         │      GROQ (M2 only)     │
│   (no API needed)       │         │                         │
│   Job: DETECT problems  │   ────► │   Job: WRITE the fix    │
└─────────────────────────┘         └─────────────────────────┘
```

This repo currently ships **M1**: the deterministic, no-LLM detection layer.
You already get a ranked list of your worst functions plus a sortable HTML
report. M2 adds Groq-powered fix suggestions.

## Install (editable, for hacking)

```bash
pip install -e .
```

## Usage

```bash
airead scan path/to/your/project       # terminal table of worst functions
airead report path/to/your/project     # writes airead-report.html
```

Try it on the bundled sample:

```bash
airead scan samples
airead report samples
open airead-report.html
```

## Roadmap

- **M1** (this release): static analyzers, `scan`, `report`
- **M2**: Groq judge + interactive `next` command (warn → suggest → approve)
- **M3**: safe diff application gated by your project's tests
