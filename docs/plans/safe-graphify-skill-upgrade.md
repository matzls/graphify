---
title: "Safe Graphify Skill Upgrade Plan"
kind: plan
status: accepted
audience: "agents-maintainers"
canonicality: active-plan
doc_id: "safe-graphify-skill-upgrade"
owners:
  - "mase"
created: 2026-05-02
updated: 2026-05-02
source_of_truth: "./safe-graphify-skill-upgrade.md"
related:
  - "../mase-fork-operating-model.md"
  - "../../AGENTS.md"
  - "/Users/mase/.codex/skills/graphify/SKILL.md"
  - "/Users/mase/.codex/docs/reference/graphify.md"
tags:
  - "graphify"
  - "codex"
  - "skill-sync"
---

# Safe Graphify Skill Upgrade Plan

## Summary

Upgrade the installed Codex Graphify skill at
`/Users/mase/.codex/skills/graphify/SKILL.md` by surgically porting only the
safe newer behavior from
`/Users/mase/Codebase/Personal-Projects/graphify/graphify/skill-codex.md`.

Preserve all existing `.codex` customizations: fork verification, bounded scan
guidance, strict ignore handling, Second Brain separation, no PyPI fallback, and
activation-after-success rules.

## Key Changes

- Add `rationale` to the semantic extraction contract:
  - Extend the doc/paper extraction prompt to allow `file_type:"rationale"` for
    concept-like rationale nodes.
  - Update the JSON schema example from `code|document|paper|image` to
    `code|document|paper|image|rationale`.
- Add durable community label output:
  - Keep writing `.graphify_labels.json`.
  - Also write `graphify-out/community_labels.json` with sorted JSON keys so
    watch/code-only rebuilds can preserve semantic community labels.
- Fix semantic chunk merge handling safely:
  - Add a merge block in Step B3 that reads
    `graphify-out/.graphify_chunk_*.json`.
  - Merge valid chunks into `.graphify_semantic_new.json`, because later
    cache/merge steps currently read that root file.
  - Also mirror the same merged payload to
    `graphify-out/.graphify_semantic_new.json` for audit/debug visibility.
  - Do not copy the repo skill verbatim here, because its Codex version writes
    only to `graphify-out/.graphify_semantic_new.json` while later reading
    `.graphify_semantic_new.json`.
- Leave wiki export out for now:
  - Do not add `--wiki` to the Codex skill in this pass.
  - Treat wiki as a separate output-surface decision.

## Implementation Steps

- Before editing, inspect the current `.codex` diff and preserve the existing
  dirty local changes in:
  - `/Users/mase/.codex/skills/graphify/SKILL.md`
  - `/Users/mase/.codex/docs/reference/graphify.md`
- Patch only `/Users/mase/.codex/skills/graphify/SKILL.md`.
- Use a targeted patch, not file replacement.
- Keep the current top-level Purpose, When To Use, Preconditions, and Procedure
  sections intact.
- Do not modify
  `/Users/mase/Codebase/Personal-Projects/graphify/graphify/skill-codex.md`
  unless separately requested.

## Test Plan

Run non-mutating verification after patch:

```bash
rg -n "rationale|community_labels|graphify_semantic_new|graphify_chunk|--wiki" /Users/mase/.codex/skills/graphify/SKILL.md
git -C /Users/mase/.codex diff -- skills/graphify/SKILL.md docs/reference/graphify.md
git -C /Users/mase/.codex diff --check -- skills/graphify/SKILL.md docs/reference/graphify.md
```

Acceptance criteria:

- `.codex` skill includes `file_type:"rationale"` and schema includes
  `rationale`.
- `.codex` skill writes both `.graphify_labels.json` and
  `graphify-out/community_labels.json`.
- `.codex` skill merges chunk files into root `.graphify_semantic_new.json`.
- Existing custom `.codex` safety guidance remains present.
- No `--wiki` workflow is added.
- No source-code tests are required because this is a skill-doc change only.

## Assumptions

- The implementation target is the installed Codex skill, not the Graphify
  runtime source.
- Existing dirty `.codex` changes are intentional and must be preserved.
- This pass should improve current behavior without expanding the advertised
  output surface.
