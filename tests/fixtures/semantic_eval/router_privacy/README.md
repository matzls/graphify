# Message Router Privacy Fixture

The message router accepts inbound support messages through the intake adapter.
Before any classifier runs, the redaction stage removes secrets, mailbox ids,
and customer contact details. The classifier only receives redacted message
summaries and emits a routing decision.

Each routing decision writes an audit event with the selected queue, the
classifier label, and the retention marker. Messages that mention legal review
or consent withdrawal are sent to the escalation queue instead of the automatic
reply queue.
