---
description: List past tech-scout research runs — newest first. Useful before starting a new run to see what's already been covered.
argument-hint: '[--root PATH] [--limit N]'
---

# /tech-scout-list — List past research runs

The user wants to see what's been researched before. Output a clean table.

User's arguments: $ARGUMENTS

## What to do

1. Determine the research-documentation root:
   - If `--root PATH` provided, use it.
   - Otherwise, use the configured default from `Settings.default_output_root` (override via `TECH_SCOUT_DEFAULT_OUTPUT_ROOT`).
2. Determine the limit (default 20).
3. Bash:
   ```bash
   python scripts/ts_list_history.py "<root>" --limit <N>
   ```
4. Parse the JSON envelope. Render a markdown table:

```markdown
**Past research runs** (newest → oldest)

| Date | Title | Slug | Topic Summary |
|------|-------|------|---------------|
| 2026-04-22 | Memory Layer for AI Agents | `memory-layer-ai-agents` | ... |
| 2026-04-15 | MCP Protocol Deep Dive | `mcp-protocol-deep-dive` | ... |
```

5. After the table, print:
   - **Total**: how many runs in history
   - **Returned**: how many shown (might be less if `--limit` was hit)
   - Tip: "`/tech-scout-show <slug>` to view details."

## On error

- Root not found → say "No research runs yet (root folder doesn't exist). Start with `/tech-scout`."
- Helper script returns error → surface the message.

## No state changes

This command is read-only. Don't write any files.
