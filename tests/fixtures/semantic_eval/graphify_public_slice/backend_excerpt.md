# Graphify Backend Excerpt

The direct semantic backend path supports Ollama, Gemini, Kimi, Claude, OpenAI,
DeepSeek, Azure, Bedrock, and claude-cli. The local fork standardizes automatic
semantic extraction on the Ollama backend with kimi-k2.7-code:cloud as the default
model.

Graphify validates backend dependencies before semantic extraction. Trace mode
prints backend, model, host, timing, finish reason, and token counts without
printing raw prompts, model output, API keys, or document content.

The semantic cache prevents unchanged document, paper, and image files from
being re-extracted on repeated runs.
