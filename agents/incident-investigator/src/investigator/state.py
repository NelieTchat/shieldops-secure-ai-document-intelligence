"""Shared types, limits and input validation for the Incident Investigator (ADR 0011, MVP-1)."""
import re
from typing import Any, Literal, TypedDict

ALLOWED_TOOLS = (
    "get_pod_status",
    "get_pod_events",
    "get_deployment_status",
    "search_cloudwatch_logs",
)
MAX_TOOL_CALLS = 8
MAX_EVIDENCE_CHARS = 4000
MAX_TEXT_CHARS = 2000
MAX_DESCRIPTION_CHARS = 2000
DEFAULT_WINDOW_MINUTES = 30
MAX_WINDOW_MINUTES = 180

K8S_NAME = re.compile(r"[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?")
LOG_GROUP = re.compile(r"[A-Za-z0-9_./#-]{1,512}")

Confidence = Literal["low", "medium", "high"]


class Diagnosis(TypedDict):
    summary: str
    likely_cause: str
    confidence: Confidence
    evidence_refs: list[int]


class Evidence(TypedDict):
    tool: str
    args: dict[str, Any]
    ok: bool
    result: str


class Incident(TypedDict, total=False):
    description: str
    namespace: str
    service: str
    log_group: str
    window_minutes: int


class State(TypedDict):
    incident: Incident
    plan: list[dict[str, Any]]
    evidence: list[Evidence]
    diagnosis: Diagnosis | None
    reasoning_failed: bool
    report: str


class InvalidIncident(ValueError):
    """Raised for a malformed incident. Messages never echo the rejected value."""


def validate_incident(raw: Any) -> Incident:
    if not isinstance(raw, dict):
        raise InvalidIncident("The incident must be an object.")
    description = raw.get("description")
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= MAX_DESCRIPTION_CHARS:
        raise InvalidIncident("The description must be 1 to 2000 characters.")
    for field in ("namespace", "service"):
        value = raw.get(field)
        if not isinstance(value, str) or not K8S_NAME.fullmatch(value):
            raise InvalidIncident("The " + field + " is not a valid Kubernetes name.")
    incident: Incident = {
        "description": description.strip(),
        "namespace": raw["namespace"],
        "service": raw["service"],
        "window_minutes": DEFAULT_WINDOW_MINUTES,
    }
    log_group = raw.get("log_group")
    if log_group is not None:
        if not isinstance(log_group, str) or not LOG_GROUP.fullmatch(log_group):
            raise InvalidIncident("The log group name is not valid.")
        incident["log_group"] = log_group
    window = raw.get("window_minutes", DEFAULT_WINDOW_MINUTES)
    if isinstance(window, bool) or not isinstance(window, int) or not 1 <= window <= MAX_WINDOW_MINUTES:
        raise InvalidIncident("The window must be 1 to 180 minutes.")
    incident["window_minutes"] = window
    return incident
