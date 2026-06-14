def build_hydration_packet(source_id: str, decision_records: list[str]) -> dict:
    return {
        "source_id": source_id,
        "decision_records": decision_records,
        "stale_state_marker": "required",
    }


def validate_packet(packet: dict, approved: bool) -> bool:
    return bool(packet.get("stale_state_marker") and approved)
