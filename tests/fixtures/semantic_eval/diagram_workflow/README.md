# Diagram Workflow Fixture

This fixture tests image-based semantic extraction. The authoritative workflow is
shown in `diagram.png`; the surrounding text intentionally gives only this
summary so a model must inspect the image to recover the full node names and
branching structure.

The diagram depicts a routing workflow with a normal path and a manual review
path. The extracted graph should cite `diagram.png` for visual concepts.
