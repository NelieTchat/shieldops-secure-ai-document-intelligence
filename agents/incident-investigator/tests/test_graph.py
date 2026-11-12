import pytest

from investigator.graph import build_plan, investigate, make_gather, sanitize_diagnosis
from investigator.state import (
    ALLOWED_TOOLS, MAX_EVIDENCE_CHARS, MAX_TOOL_CALLS, InvalidIncident, validate_incident,
)

INCIDENT = {
    "description": "api returns 500 on upload",
    "namespace": "shieldops-apps",
    "service": "api",
    "log_group": "/aws/eks/shieldops/api",
}


def make_tools(calls, fail=(), big=False):
    def build(name):
        def run(**kwargs):
            calls.append((name, kwargs))
            if name in fail:
                raise RuntimeError("secret detail that must never leak")
            return "x" * 10000 if big else {"tool": name, "items": [1, 2]}
        return run
    return {name: build(name) for name in ALLOWED_TOOLS}


def make_reasoner(seen, answer=None):
    def reasoner(incident, evidence):
        seen.append(len(evidence))
        return answer or {"summary": "Uploads fail.", "likely_cause": "Missing S3 permission.",
                          "confidence": "high", "evidence_refs": [0, 1]}
    return reasoner


def test_the_full_flow_gathers_evidence_reasons_and_reports():
    calls, seen = [], []
    state = investigate(INCIDENT, make_tools(calls), make_reasoner(seen))
    assert [name for name, _ in calls] == [
        "get_deployment_status", "get_pod_status", "get_pod_events", "search_cloudwatch_logs"]
    assert seen == [4]
    assert state["diagnosis"]["confidence"] == "high"
    assert "Missing S3 permission." in state["report"]
    assert "No actions were taken" in state["report"]


def test_a_failing_tool_is_recorded_by_type_only_and_the_rest_still_run():
    calls, seen = [], []
    state = investigate(INCIDENT, make_tools(calls, fail={"get_pod_events"}), make_reasoner(seen))
    failed = [item for item in state["evidence"] if not item["ok"]]
    assert len(failed) == 1 and failed[0]["result"] == "RuntimeError"
    assert len(calls) == 4
    assert "secret detail" not in state["report"]


def test_with_no_usable_evidence_the_model_is_never_called():
    calls, seen = [], []
    state = investigate(INCIDENT, make_tools(calls, fail=set(ALLOWED_TOOLS)), make_reasoner(seen))
    assert seen == []
    assert state["diagnosis"] is None
    assert "Insufficient evidence" in state["report"]


def test_a_reasoner_failure_is_reported_without_its_message():
    def broken(incident, evidence):
        raise ValueError("leak me")
    state = investigate(INCIDENT, make_tools([]), broken)
    assert state["reasoning_failed"] is True
    assert "leak me" not in state["report"]
    assert "reasoning step failed" in state["report"]


def test_a_tool_outside_the_allowlist_is_refused_and_never_called():
    calls = []
    gather = make_gather(make_tools(calls))
    plan = [{"tool": "run_command", "args": {"cmd": "kubectl delete pod x"}}]
    evidence = gather({"plan": plan})["evidence"]
    assert evidence[0]["ok"] is False and "refused" in evidence[0]["result"]
    assert calls == []


def test_the_number_of_tool_calls_is_capped():
    calls = []
    gather = make_gather(make_tools(calls))
    plan = [{"tool": "get_pod_status", "args": {"namespace": "a", "app": "b"}}] * 20
    assert len(gather({"plan": plan})["evidence"]) == MAX_TOOL_CALLS
    assert len(calls) == MAX_TOOL_CALLS


def test_oversized_tool_output_is_truncated():
    state = investigate(INCIDENT, make_tools([], big=True), make_reasoner([]))
    for item in state["evidence"]:
        assert len(item["result"]) <= MAX_EVIDENCE_CHARS + 30
        assert item["result"].endswith("[truncated]")


def test_the_plan_only_names_allowed_tools_and_skips_logs_without_a_log_group():
    without_logs = {k: v for k, v in INCIDENT.items() if k != "log_group"}
    plan = build_plan(validate_incident(without_logs))
    assert {call["tool"] for call in plan} <= set(ALLOWED_TOOLS)
    assert "search_cloudwatch_logs" not in {call["tool"] for call in plan}


def test_confidence_is_forced_to_low_without_valid_evidence_references():
    evidence = [{"tool": "t", "args": {}, "ok": False, "result": "RuntimeError"}]
    claimed = {"summary": "s", "likely_cause": "c", "confidence": "high", "evidence_refs": [0, 5, True]}
    assert sanitize_diagnosis(claimed, evidence)["confidence"] == "low"
    assert sanitize_diagnosis(claimed, evidence)["evidence_refs"] == []


def test_unknown_confidence_values_become_low():
    evidence = [{"tool": "t", "args": {}, "ok": True, "result": "r"}]
    claimed = {"summary": "s", "likely_cause": "c", "confidence": "certain", "evidence_refs": [0]}
    assert sanitize_diagnosis(claimed, evidence)["confidence"] == "low"


@pytest.mark.parametrize("change", [
    {"namespace": "Bad_NS"},
    {"service": "has space"},
    {"log_group": "bad group name"},
    {"window_minutes": 0},
    {"window_minutes": 9999},
    {"window_minutes": True},
    {"description": "   "},
])
def test_malformed_incidents_are_rejected(change):
    with pytest.raises(InvalidIncident):
        validate_incident({**INCIDENT, **change})


def test_validation_errors_never_echo_the_rejected_value():
    with pytest.raises(InvalidIncident) as error:
        validate_incident({**INCIDENT, "namespace": "Bad_NS;rm -rf"})
    assert "rm -rf" not in str(error.value)
