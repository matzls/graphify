# Graphify Architecture Excerpt

Graphify uses a staged pipeline: detect files, extract nodes and edges, build a
NetworkX graph, cluster communities, analyze god nodes and surprising
connections, then generate reports and exports.

The detect stage classifies code, documents, papers, images, and media. Code
extraction is deterministic and local through language extractors. Semantic
extraction handles documents, papers, and images through an LLM backend.

Graph outputs are written under graphify-out. The main durable artifacts are
graph.json, GRAPH_REPORT.md, community labels, manifest data, and optional wiki
or HTML exports.
