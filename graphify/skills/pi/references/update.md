# graphify reference: incremental update and cluster-only

Load this only when the user passed `--update` or `--cluster-only`. A first-time
full build never reads this file.

CLI-backed skills use Graphify's CLI backend path. Do not reconstruct the older
manual AST/semantic/subagent pipeline from this reference; the CLI owns
incremental rebuilds, semantic refreshes, clustering, reports, and wiki output.

## For --update

Use this when files changed since the last graph build and the user explicitly
asked for `/graphify <path> --update` or `/graphify --update`.

`graphify update` is deterministic and code-only. It does not spend LLM tokens
and does not refresh semantic relationships for docs, papers, images, or media.

Build the command from the original invocation:

- Use the original path as `INPUT_PATH`; if no path was provided, use `.`.
- Pass `--no-cluster` when the user supplied it.
- Pass `--force` only when the user supplied it or the user explicitly asks to
  override Graphify's shrink/update guards.

Run:

```bash
graphify update INPUT_PATH
```

Examples:

```bash
graphify update .
graphify update INPUT_PATH --no-cluster
graphify update INPUT_PATH --force
```

If `graphify update` exits non-zero, stop and report the failure. Do not run
semantic refresh, clustering, exports, or cleanup as if the update succeeded.

After a successful code-only update:

1. Check whether `graphify-out/needs_update` exists, or whether the user changed
   docs, papers, images, media, or mixed corpus content and semantic
   relationships matter for the current task.
2. If semantic refresh does not matter, report that the code graph was updated
   and that semantic content still needs the backend refresh sequence when it
   matters.
3. If semantic refresh does matter, run the backend semantic sequence below.

### Backend semantic refresh after --update

Run this only when semantic relationships matter for changed docs, papers,
images, media, or mixed corpus content, or when the user explicitly asked for a
semantic refresh.

Build the commands from the original invocation:

- Always include `--backend ollama` unless the user explicitly supplied another
  backend flag.
- Include `--model <value>` only when the user supplied `--model <value>`; do
  not hardcode the default model. Model resolution is explicit `--model`, then
  `OLLAMA_MODEL`, then Graphify's built-in default
  `deepseek-v4-pro:cloud`.
- Pass through `--mode deep`, `--directed`, `--whisper-model <value>`, and
  `--no-cluster` to `extract` when present.
- Pass `--no-viz` to `cluster-only` when present.

Run:

```bash
graphify extract INPUT_PATH --backend ollama
graphify cluster-only INPUT_PATH --backend ollama
```

Examples:

```bash
graphify extract INPUT_PATH --backend ollama --mode deep
graphify extract INPUT_PATH --backend ollama --model EXPLICIT_MODEL
graphify cluster-only INPUT_PATH --backend ollama --no-viz
graphify cluster-only INPUT_PATH --backend ollama --model EXPLICIT_MODEL
```

If `graphify extract` exits non-zero, stop. Do not proceed to `cluster-only`,
exports, cleanup, or report pasteback. If `cluster-only` exits non-zero, report
that the semantic extraction completed but report/wiki/label refresh failed.

## For --cluster-only

Use this when the user explicitly asks to rerun clustering/labeling on an
existing graph.

Build the command from the original invocation:

- Use the original path as `INPUT_PATH`; if no path was provided, use `.`.
- Always include `--backend ollama` unless the user explicitly supplied another
  backend flag.
- Include `--model <value>` only when the user supplied `--model <value>`.
- Pass `--no-viz` when present.

Run:

```bash
graphify cluster-only INPUT_PATH --backend ollama
```

`graphify cluster-only` is self-contained: it re-clusters, names communities,
regenerates `GRAPH_REPORT.md`, refreshes `graph.json`, generates `graph.html`
unless `--no-viz` was passed, and refreshes wiki output when semantic state is
clean. Do not run the first-time build's intermediate-file steps after it; those
steps expect temporary files that prior runs clean up.

When it finishes, verify the requested outputs exist and present the refreshed
`GRAPH_REPORT.md` summary as usual.
