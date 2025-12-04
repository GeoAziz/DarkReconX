# DarkReconX Visual & Output UX Guide (Draft)

This document is a living draft describing the CLI output formats and visual conventions used by DarkReconX.

## Overview

DarkReconX supports three primary output formats:

- `pretty` (default): Human-friendly terminal output using Rich panels and tables.
- `json`: Machine-friendly JSON for scripting and post-processing.
- `md`: Markdown report suitable for saving as a document or including in a shareable report.

All commands accept a global `--format`/`-f` option and verbosity flags `-v` / `-vv`.

## Output examples

### Pretty (terminal)

A `pretty` result will include:
- Header panel with target and type
- Summary table with counts (IPs, DNS records, etc.)
- Optional WHOIS and Network tables when verbosity is enabled
- Risk Assessment panel when risk data exists

### JSON

`--format json` prints a pretty-printed JSON representation of the unified record. Use this with scripts or to pipe into other tools.

Example:

```
$ darkreconx domain example.com --format json | jq '.'
```

### Markdown

`--format md` emits a Markdown document with a `# Report: <target>` header, a summary section, and raw JSON data if verbosity is requested.

Example:

```
$ darkreconx domain example.com --format md > example_report.md
```

## Verbosity

- No `-v`: concise summary (default)
- `-v`: include WHOIS & Network tables
- `-vv`: include raw provider responses or full JSON sections in Markdown output

## Integration guidance

- Modules should not write directly to stdout; instead they should return structured `UnifiedRecord` dicts that the CLI passes to the central renderer (`core.render.render_output`).
- This ensures consistent formatting and makes it trivial to add new output formats later (e.g., HTML, CSV).

## File locations

- Renderer: `core/render.py`
- CLI entrypoint: `cli/main.py`
- UX guide: this file `docs/UX_GUIDE.md`

## Next steps

- Add per-module migration to use `core.render` instead of ad-hoc prints.
- Add more examples and screenshots to this doc.
- Consider adding an HTML export format for richer report sharing.
