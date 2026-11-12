"""LangGraph state machine for the Incident Investigator (ADR 0011, MVP-1).

The graph has no infrastructure authority. Tools are injected, limited to an allowlist,
capped in number and in output size, and can only read. The model (the reasoner) is
injected too and only returns a diagnosis: it cannot call tools or trigger any action.
Exception messages are never kept, only exception type names.
"""
import json
from collections.abc import Callable, Mapping
from typing import Any

from langgraph.graph import END, START, StateGraph

from .report import render_report
from .state import (
    ALLOWED_TOOLS,
    DEFAULT_WINDOW_MINUTES,
    MAX_EVIDENCE_CHARS,
    MAX_TEXT_CHARS,
    MAX_TOOL_CALLS,
    State,
    validate_incident,
)

LOG_FILTER = "?ERROR ?AccessDenied ?Throttling ?Timeout"

Tools = Mapping[str, Callable[..., Any]]
Reasoner = Callable[[Any, list], Mapping[str, Any]]


def build_plan(incident) -> list[dict[str, Any]]:
    namespace, service = incident["namespace"], incident["service"]
    calls = [
        {"tool": "get_deployment_status", "args": {"namespace": namespace, "name": service}},
        {"tool": "get_pod_status", "args": {"namespace": namespace, "app": service}},
        {"tool": "get_pod_events", "args": {"namespace": namespace, "app": service}},
    ]
    if incident.get("log_group"):
        calls.append({
            "tool": "search_cloudwatch_logs",
            "args": {
                "log_group": incident["log_group"],
                "filter_pattern": LOG_FILTER,
                "window_minutes": incident.get("window_minutes", DEFAULT_WINDOW_MINUTES),
            },
        })
    return calls


def _bounded(result: Any) -> str:
    text = result if isinstance(result, str) else json.dumps(result, default=str, sort_keys=True)
    if len(text) > MAX_EVIDENCE_CHARS:
        return text[:MAX_EVIDENCE_CHARS] + "\n... [truncated]"
    return text


def _evidence(tool, args, ok, result):
    return {"tool": tool, "args": args, "ok": ok, "result": result}


def make_gather(tools: Tools):
    def gather(state):
        evidence = []
        for call in state["plan"][:MAX_TOOL_CALLS]:
            name = call.get("tool")
            args = dict(call.get("args", {}))
            if name not in ALLOWED_TOOLS:
                evidence.append(_evidence(str(name)[:60], args, False, "refused: tool not allowed"))
                continue
            function = tools.get(name)
            if function is None:
                evidence.append(_evidence(name, args, False, "tool unavailable"))
                continue
            try:
                result = function(**args)
            except Exception as error:
                evidence.append(_evidence(name, args, False, type(error).__name__))
                continue
            evidence.append(_evidence(name, args, True, _bounded(result)))
        return {"evidence": evidence}

    return gather


def sanitize_diagnosis(raw: Any, evidence: list) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError("the diagnosis must be a mapping")
    refs_in = raw.get("evidence_refs")
    refs: list[int] = []
    for ref in refs_in if isinstance(refs_in, list) else []:
        valid = isinstance(ref, int) and not isinstance(ref, bool) and 0 <= ref < len(evidence)
        if valid and evidence[ref]["ok"] and ref not in refs:
            refs.append(ref)
    confidence = raw.get("confidence")
    if confidence not in ("low", "medium", "high") or not refs:
        confidence = "low"
    return {
        "summary": str(raw.get("summary", ""))[:MAX_TEXT_CHARS],
        "likely_cause": str(raw.get("likely_cause", ""))[:MAX_TEXT_CHARS],
        "confidence": confidence,
        "evidence_refs": refs,
    }


def make_reason(reasoner: Reasoner):
    def reason(state):
        try:
            raw = reasoner(state["incident"], state["evidence"])
            return {"diagnosis": sanitize_diagnosis(raw, state["evidence"]), "reasoning_failed": False}
        except Exception:
            return {"diagnosis": None, "reasoning_failed": True}

    return reason


def _plan_node(state):
    return {"plan": build_plan(state["incident"])}


def _report_node(state):
    return {"report": render_report(state)}


def _after_gather(state):
    return "reason_over_evidence" if any(item["ok"] for item in state["evidence"]) else "write_report"


def build_graph(tools: Tools, reasoner: Reasoner):
    graph = StateGraph(State)
    graph.add_node("make_plan", _plan_node)
    graph.add_node("gather_evidence", make_gather(tools))
    graph.add_node("reason_over_evidence", make_reason(reasoner))
    graph.add_node("write_report", _report_node)
    graph.add_edge(START, "make_plan")
    graph.add_edge("make_plan", "gather_evidence")
    graph.add_conditional_edges(
        "gather_evidence", _after_gather,
        {"reason_over_evidence": "reason_over_evidence", "write_report": "write_report"},
    )
    graph.add_edge("reason_over_evidence", "write_report")
    graph.add_edge("write_report", END)
    return graph.compile()


def investigate(raw_incident: Any, tools: Tools, reasoner: Reasoner) -> dict[str, Any]:
    incident = validate_incident(raw_incident)
    app = build_graph(tools, reasoner)
    return app.invoke({
        "incident": incident, "plan": [], "evidence": [],
        "diagnosis": None, "reasoning_failed": False, "report": "",
    })
