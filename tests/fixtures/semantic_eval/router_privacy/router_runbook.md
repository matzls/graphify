# Router Runbook

When triaging a message, operators inspect the audit event first. If the audit
event has no retention marker, the operator pauses routing and files a privacy
review task.

For normal support messages, verify that the intake adapter, redaction stage,
classifier, and routing decision all appear in the same trace event. For consent
withdrawal or legal-review messages, confirm that the escalation queue received
the redacted summary.
