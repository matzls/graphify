# Plan Brief Workflow

<purpose>
Create or verify human-readable `*-BRIEF.md` companions for executable `*-PLAN.md`
artifacts.

The brief is derived evidence. It helps humans understand the plan at a project
or product-manager level, but the source `PLAN.md` remains authoritative.
</purpose>

<process>

## 1. Resolve Target

Read `{{GSD_ARGS}}` as either:
- a concrete `*-PLAN.md` path
- a phase directory
- a phase number or phase slug

If no target is supplied, ask for a target instead of guessing.

## 2. Generate Or Check

Use the compatibility helper for deterministic generation and freshness checks:

```bash
node "/Users/mase/Codebase/Personal-Projects/graphify/.codex/get-shit-done/bin/gsd-tools.cjs" plan-brief "$TARGET"
```

For freshness-only mode:

```bash
node "/Users/mase/Codebase/Personal-Projects/graphify/.codex/get-shit-done/bin/gsd-tools.cjs" plan-brief "$TARGET" --check
```

The helper writes one `*-BRIEF.md` sibling for each `*-PLAN.md` target and
records `source_plan_hash` as a SHA-256 hash of the source plan content with
line endings normalized to LF.

## 3. Report

Print a concise result:
- generated or checked count
- produced `*-BRIEF.md` path(s) as markdown file links, using the basename as
  the label and the absolute path as the target:
  `[04-01-BRIEF.md](/absolute/path/to/04-01-BRIEF.md)`
  If the absolute path contains spaces, wrap only the markdown target in angle
  brackets: `[04-01-BRIEF.md](</absolute/path with spaces/04-01-BRIEF.md>)`.
- stale or missing brief count when `--check` is used

If a brief is stale, regenerate it with the same command without `--check`.

</process>
