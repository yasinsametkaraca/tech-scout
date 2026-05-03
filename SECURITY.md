# Security Policy

## Supported Versions

| Version | Status | Security fixes |
|---------|--------|----------------|
| `0.1.x` | Active | Yes (current) |
| `< 0.1` | Pre-release | No |

We follow semver. Security patches land in the latest minor of the
supported major. Older majors do not receive backports.

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for a security report.**
Instead, e-mail the maintainer at
**`yasinsamet.karaca@gmail.com`** with the subject line
`tech-scout security:` followed by a one-line summary.

In your report, include:

1. **Affected version(s)** — `0.1.0`, `main` branch, etc.
2. **Description** — what the vulnerability is, in plain language.
3. **Reproduction** — the smallest sequence of steps that demonstrates
   it. If a malicious input is involved, attach the input verbatim or
   describe how to construct it.
4. **Impact assessment** — what an attacker could achieve (e.g.,
   "directory traversal escapes the output folder", "audit-log
   tampering").
5. **(Optional) Suggested fix** — a patch or a sketch of one is
   welcomed but not required.

We will:

- **Acknowledge** receipt within **3 business days**.
- **Investigate** and confirm or rule out the issue within **14 days**.
- **Coordinate disclosure**: agree on a fix window with you (typically
  ≤90 days), prepare a patch and an advisory, then release them
  together.
- **Credit you** in the release notes and the GitHub Security Advisory
  unless you prefer to remain anonymous.

If the vulnerability is being actively exploited or you believe the
default 14-day window is too long, mention that in your report and we
will accelerate.

---

## Scope

This project ships:

- A Python library (`src/tech_scout/`).
- Helper CLI commands (`tech_scout.cli.*`).
- Jinja2 templates and locale specs (data only — no executable user
  input).
- A Claude Code plugin definition (markdown files under `.claude/`).

In scope:

- Anything that can corrupt persisted run state, leak sensitive content
  out of the output folder, escape directory traversal, or bypass the
  package validator.
- Anything that lets a malicious manifest file (e.g., a crafted
  `pyproject.toml`) execute arbitrary code during scanning.
- Anything that lets a crafted candidate JSON or render-context JSON
  escape Jinja2 sandboxing.

Out of scope:

- Vulnerabilities in upstream dependencies — please report those to the
  affected maintainer. We will pull in fixes promptly when they ship.
- Issues that require the user to deliberately disable safety features
  (`--no-verify`, `shell=True`, etc.).
- Performance regressions.

---

## What This Project Does Not Do

- **No network calls except via Claude Code's tools.** The Python
  helpers do not make HTTP requests. Discovery and analysis happen
  inside the Claude Code skill, using its built-in `WebSearch` and
  `WebFetch` tools.
- **No code execution from manifests.** The Python manifest reader
  parses `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`
  (presence-only — the file is never executed). Same for Cargo.toml,
  package.json, go.mod, and so on.
- **No secrets in state files.** State files (`state.json`,
  `candidates.json`, `selection.json`, `audit.jsonl`) carry only the
  public per-run metadata.

If a future change introduces network calls or arbitrary execution,
this section will be updated and a major version bump will follow.
