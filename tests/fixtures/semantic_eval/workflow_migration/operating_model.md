# Agent Workflow Operating Model

The migration runner reads source memory packets and converts them into a
hydration packet for the new agent runtime. A hydration packet is also called a
handoff packet in operator notes. The migration adapter preserves source ids,
decision records, and stale-state markers.

Operator approval is required before the migration adapter writes durable state.
If validation fails, the rollback note explains which hydration packet was
rejected and why.
