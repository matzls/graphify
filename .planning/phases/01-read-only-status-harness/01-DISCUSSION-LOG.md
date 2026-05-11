# Phase 1: Read-Only Status Harness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 1-Read-Only Status Harness
**Areas discussed:** Harness shape, output contract, diagnosis model, Second Brain targeting, Ollama generation checks, baseline reports

---

## Harness Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Public CLI command now | Add a user-facing Graphify command immediately. | |
| Internal/dev harness first | Keep it in the fork as an evaluation tool and promote later if stable. | ✓ |
| Local planning helper only | Keep it outside Graphify source entirely. | |

**User's choice:** Followed the recommendation to avoid a CLI command for now.
**Notes:** The harness should be repeatable and structured, but Phase 1 is still discovery around the right checks and report shape.

---

## Output Contract

| Option | Description | Selected |
|--------|-------------|----------|
| JSON only | Machine-readable report only. | |
| JSON and short Markdown | JSON as source of truth plus concise summary. | ✓ |
| Markdown only | Human-readable summary only. | |

**User's choice:** Both JSON and Markdown.
**Notes:** Markdown should stay short and agent-readable, especially around diagnosis and next action.

---

## Diagnosis Model

| Option | Description | Selected |
|--------|-------------|----------|
| Strict by default | Treat stale/missing consumer graph expectations as failures. | |
| Diagnostic by default | Fail broken source/install/profile guarantees, warn on stale artifacts. | ✓ |
| Informational only | Avoid pass/warn/fail classification. | |

**User's choice:** Followed the recommendation for diagnostic-by-default.
**Notes:** Strict mode is useful later for recurring acceptance checks, but Phase 1 should not overstate failure while the baseline is still being established.

---

## Second Brain Targeting

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcode Second Brain checks | Build only for the current target repo. | |
| Profile-driven Second Brain checks | Use a target profile or profile-like config for Second Brain-specific expectations. | ✓ |
| Fully generic only | Avoid target-specific expectations. | |

**User's choice:** Second Brain-specific checks are desired.
**Notes:** The captured decision is to express those through profile data so the harness remains reusable.

---

## Ollama Generation Checks

| Option | Description | Selected |
|--------|-------------|----------|
| Detect-only | Only verify backend and model availability. | |
| Small smoke only | Run a minimal local generation check. | |
| Small smoke plus stress | Run both a small and a larger local generation/stress check. | ✓ |

**User's choice:** Definitely run local generation smoke tests, including bigger-file stress behavior.
**Notes:** The checks should not implicitly refresh Second Brain in Phase 1.

---

## Baseline Reports

| Option | Description | Selected |
|--------|-------------|----------|
| Print only | Do not save reports. | |
| Save local reports | Persist local reports for tracking over time. | ✓ |

**User's choice:** Save local reports for tracking.
**Notes:** Reports should be saved in a controlled local output location rather than creating accidental target repo churn.

## the agent's Discretion

- Exact internal module/file layout.
- Exact report directory and JSON schema details.
- Exact temporary fixture shape for generation stress tests.

## Deferred Ideas

- Public Graphify CLI command for the harness.
- Strict recurring acceptance mode.
- Approved Second Brain semantic refresh followed by stricter post-refresh expectations.
