# graphify reference: commit hook and native AGENTS.md integration

Load this when the user asked to install the post-commit hook or wire graphify into a project's AGENTS.md.

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
graphify hook install    # install
graphify hook uninstall  # remove
graphify hook status     # check
```

After every `git commit`, the hook classifies changed paths. Code changes trigger a deterministic AST extraction and graph rebuild for the changed files; no LLM is used. Documentation, papers, media, and image changes write `graphify-out/needs_update` so a later semantic refresh can process them.

If a post-commit hook already exists, graphify appends to it rather than replacing it.

---

## For native AGENTS.md integration@@AGENTS_HEADING_SUFFIX@@

Run once per project to make graphify always-on in @@HOST_DISPLAY@@ sessions:

```bash
@@AGENTS_INSTALL_BLOCK@@
```

This writes a `## graphify` section to the local `AGENTS.md` that instructs @@HOST_DISPLAY@@ to check the graph before answering codebase questions and rebuild it after code changes. No manual `/graphify` needed in future sessions.
@@AGENTS_PRETOOLUSE_NOTE@@
```bash
@@AGENTS_UNINSTALL_BLOCK@@
```
