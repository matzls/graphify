# Privacy Contract

The consent boundary is mandatory for every inbound message. The router must not
store raw mailbox exports, must not send secrets to external vendors, and must
not bypass consent checks. Only redacted message summaries may be retained.

The retention marker records when a redacted summary can be deleted. The audit
event must reference the retention marker so operators can prove the routing
workflow followed the privacy contract.
