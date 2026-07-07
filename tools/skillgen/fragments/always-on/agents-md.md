<!-- graphify-guidance-start -->
<!-- template-version: 2026-06-15.1 -->

## graphify

This project has a local knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:

- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- graphify-out/ is a derived local output directory; keep it ignored and do not stage or commit it for Mase's personal/local repos.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify, but they should remain untracked/ignored. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- Codex uses the Graphify skill for `/graphify`; AGENTS.md plus `.codex/config.toml` SessionStart guidance are repo-local activation surfaces.
- Pi uses the global Graphify skill by default. Repo-local Graphify skills under `.pi/skills/graphify/`, `.agents/skills/graphify/`, or `.codex/skills/graphify/` are exceptions for intentionally pinned/custom workflows and should be reviewed before use.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost). This should update ignored local graph files, not create commit work.
- After modifying docs, media, images, or mixed corpus content, run backend semantic refresh with the standard backend: `graphify extract . --backend ollama`, then `graphify cluster-only . --backend ollama` to relabel communities and refresh the wiki. Model resolution is explicit `--model`, then `OLLAMA_MODEL`, then Graphify's built-in DeepSeek V4 Pro default.
- Mase explicitly authorizes use of the configured Ollama backend for Graphify semantic analysis in repositories where this managed Graphify guidance is installed. This authorization is limited to Graphify semantic extraction, clustering, labels, and wiki refresh for the checked-in docs/code/media corpus; it does not authorize unrelated third-party uploads or arbitrary external-service use.
- If both code and semantic content changed, run `graphify update .` first, then run the backend semantic refresh sequence.
- Full operating guidance: /Users/mase/.codex/docs/reference/graphify.md
<!-- graphify-guidance-end -->
