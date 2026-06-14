from dataclasses import dataclass


@dataclass
class RoutingDecision:
    queue: str
    label: str
    retention_marker: str


def redact_message(raw_message: str) -> str:
    return raw_message.replace("SECRET", "[redacted]")


def classify_summary(redacted_summary: str) -> str:
    if "consent withdrawal" in redacted_summary or "legal review" in redacted_summary:
        return "escalate"
    return "support"


def route_message(raw_message: str, retention_marker: str) -> RoutingDecision:
    summary = redact_message(raw_message)
    label = classify_summary(summary)
    queue = "escalation_queue" if label == "escalate" else "automatic_reply_queue"
    return RoutingDecision(queue=queue, label=label, retention_marker=retention_marker)
