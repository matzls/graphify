# External Integrations

**Analysis Date:** 2026-05-11

## APIs & External Services

**LLM / Semantic Extraction:**
- Anthropic Claude - Direct Claude extraction backend in `graphify/llm.py`.
  - SDK/Client: `anthropic` imported in `graphify/llm.py`
  - Auth: `ANTHROPIC_API_KEY`
- Moonshot Kimi - OpenAI-compatible extraction backend in `graphify/llm.py`.
  - SDK/Client: `openai`
  - Auth: `MOONSHOT_API_KEY`
- Google Gemini - OpenAI-compatible extraction backend in `graphify/llm.py`.
  - SDK/Client: `openai`
  - Auth: `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- OpenAI - OpenAI extraction backend in `graphify/llm.py`.
  - SDK/Client: `openai`
  - Auth: `OPENAI_API_KEY`
- Ollama - Local OpenAI-compatible extraction backend in `graphify/llm.py`.
  - SDK/Client: `openai`
  - Auth: `OLLAMA_API_KEY` optional placeholder; endpoint selected by `OLLAMA_BASE_URL`
- AWS Bedrock - Bedrock Converse API extraction backend in `graphify/llm.py`.
  - SDK/Client: `boto3`
  - Auth: AWS standard credential chain via `AWS_PROFILE`, `AWS_REGION`, or `AWS_DEFAULT_REGION`

**Content Ingestion:**
- Generic web pages - Fetched through `graphify/security.py` and converted in `graphify/ingest.py`.
  - SDK/Client: Python `urllib.request`; optional `markdownify`
  - Auth: Not applicable
- X/Twitter oEmbed - Tweet extraction in `graphify/ingest.py` uses `https://publish.twitter.com/oembed`.
  - SDK/Client: Python `urllib.request` through `safe_fetch_text`
  - Auth: Not applicable
- arXiv - Abstract/page extraction in `graphify/ingest.py` uses `https://export.arxiv.org/abs/...`.
  - SDK/Client: Python `urllib.request` through `safe_fetch_text`
  - Auth: Not applicable
- YouTube and other video URLs - Audio download in `graphify/transcribe.py`.
  - SDK/Client: `yt-dlp`
  - Auth: Not detected

**Google Workspace:**
- Google Drive for desktop shortcuts - `.gdoc`, `.gsheet`, and `.gslides` export in `graphify/google_workspace.py`.
  - SDK/Client: external `gws` CLI invoked by `subprocess.run`
  - Auth: user-authenticated `gws` CLI session; enable with `GRAPHIFY_GOOGLE_WORKSPACE=1`

**Visualization CDN:**
- vis-network - Generated HTML graph visualization in `graphify/export.py` loads `https://unpkg.com/vis-network/standalone/umd/vis-network.min.js`.
  - SDK/Client: Browser script tag in generated `graph.html`
  - Auth: Not applicable

**Assistant / IDE Surfaces:**
- Claude Code, Codex, OpenCode, Aider, OpenClaw, Factory Droid, Trae, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Kiro, Pi, Hermes, and Google Antigravity - Install/uninstall commands in `graphify/__main__.py` write local skill/rule/hook files.
  - SDK/Client: Local filesystem config writes from `graphify/__main__.py` and skill files under `graphify/skill*.md`
  - Auth: Not applicable

## Data Storage

**Databases:**
- Neo4j - Optional generated Cypher and direct graph push in `graphify/export.py` and CLI export routing in `graphify/__main__.py`.
  - Connection: URI passed by CLI `--push`; password preferably from `NEO4J_PASSWORD`
  - Client: optional `neo4j` Python driver
- Local JSON graph storage - Primary graph output written by `graphify/export.py`.
  - Connection: local filesystem path, usually `graphify-out/graph.json`
  - Client: `networkx.readwrite.json_graph`
- Global graph storage - Cross-repo graph stored under the user home by `graphify/global_graph.py`.
  - Connection: local filesystem path printed/managed by `graphify global ...`
  - Client: local JSON file using `networkx.readwrite.json_graph`

**File Storage:**
- Local filesystem only for primary outputs: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.html`, `graphify-out/cache/`, `graphify-out/transcripts/`, `graphify-out/obsidian/`, and generated exports from `graphify/export.py`.
- External downloads are saved locally by `graphify/ingest.py` and `graphify/transcribe.py`.
- Google Workspace exports are written as Markdown sidecars by `graphify/google_workspace.py`.

**Caching:**
- Local cache under `graphify-out/cache/` managed by `graphify/cache.py`.
- Local media transcript reuse in `graphify/transcribe.py`.
- Local audio download reuse in `graphify/transcribe.py`.
- No Redis, Memcached, or remote cache detected.

## Authentication & Identity

**Auth Provider:**
- Custom environment-variable based provider selection in `graphify/llm.py`.
  - Implementation: `detect_backend()` checks `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `MOONSHOT_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, AWS environment, and Ollama availability in that priority order.
- AWS IAM / standard credential chain for Bedrock in `graphify/llm.py`.
  - Implementation: `boto3.Session(profile_name=..., region_name=...)`
- Google Workspace CLI auth for `gws` in `graphify/google_workspace.py`.
  - Implementation: external `gws drive files export` process; account email from shortcuts is hashed in generated frontmatter.
- Neo4j password auth in `graphify/export.py`.
  - Implementation: `GraphDatabase.driver(uri, auth=(user, password))`

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- CLI-oriented stdout/stderr messages across `graphify/__main__.py`, `graphify/llm.py`, `graphify/watch.py`, `graphify/ingest.py`, and `graphify/transcribe.py`.
- Git hooks write background rebuild logs to `${HOME}/.cache/graphify-rebuild.log` in `graphify/hooks.py`.
- No structured logging framework detected.
- No telemetry, usage tracking, or analytics are advertised in `README.md`.

## CI/CD & Deployment

**Hosting:**
- Python package distribution as `graphifyy` configured in `pyproject.toml`.
- Runtime is local CLI/MCP/filesystem; no application hosting platform detected.

**CI Pipeline:**
- GitHub Actions in `.github/workflows/ci.yml`.
- Matrix: Python 3.10 and 3.12.
- Installs `pip install -e ".[mcp,pdf,watch,sql]"` plus `pytest`.
- Runs `python -m pytest tests/ -q --tb=short`.
- Smoke checks `graphify --help` and `graphify install`.

## Environment Configuration

**Required env vars:**
- Required only for selected integrations:
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` for Gemini semantic extraction in `graphify/llm.py`.
- `MOONSHOT_API_KEY` for Kimi semantic extraction in `graphify/llm.py`.
- `ANTHROPIC_API_KEY` for Claude direct semantic extraction in `graphify/llm.py`.
- `OPENAI_API_KEY` for OpenAI semantic extraction in `graphify/llm.py`.
- `AWS_PROFILE`, `AWS_REGION`, or `AWS_DEFAULT_REGION` for Bedrock auto-detection and region/profile selection in `graphify/llm.py`.
- `OLLAMA_BASE_URL`, `GRAPHIFY_OLLAMA_MODEL`, `OLLAMA_MODEL`, and optional `OLLAMA_API_KEY` for Ollama extraction in `graphify/llm.py`.
- `NEO4J_PASSWORD` for Neo4j push without exposing the password on argv in `graphify/__main__.py`.
- `GRAPHIFY_GOOGLE_WORKSPACE=1` to enable Google Workspace shortcut export in `graphify/google_workspace.py`.
- `GRAPHIFY_WHISPER_MODEL` and `GRAPHIFY_WHISPER_PROMPT` for transcription tuning in `graphify/transcribe.py`.
- `GRAPHIFY_OUT` for custom output directory in `graphify/__main__.py`, `graphify/cache.py`, and `graphify/watch.py`.

**Secrets location:**
- Environment variables and external tool credential stores only.
- `.env` / `.env.*` files were not detected.
- Google Workspace credentials live outside this repo in the authenticated `gws` CLI environment.
- AWS credentials use the standard AWS provider chain outside this repo.

## Webhooks & Callbacks

**Incoming:**
- MCP stdio server in `graphify/serve.py`; it exposes tools `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, and `shortest_path`, plus resources such as `graphify://report` and `graphify://stats`.
- No HTTP webhook receiver detected.

**Outgoing:**
- Git hooks installed by `graphify/hooks.py` trigger background code graph rebuilds and semantic-refresh sentinel writes.
- Filesystem watcher in `graphify/watch.py` can rebuild on code changes and mark non-code semantic updates.
- Generated assistant/IDE hooks and rules are installed by platform-specific commands in `graphify/__main__.py`.
- External API calls are made by semantic backends in `graphify/llm.py`, content ingestion in `graphify/ingest.py`, audio download in `graphify/transcribe.py`, and Google Workspace export in `graphify/google_workspace.py`.

---

*Integration audit: 2026-05-11*
