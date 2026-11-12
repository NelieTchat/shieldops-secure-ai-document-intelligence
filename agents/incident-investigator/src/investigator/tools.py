"""The four read-only tools (ADR 0011, MVP-1).

Each tool validates its input, talks only to the narrow clients in clients.py, and
returns a small, safe subset of fields. Pod specs, environment variables, annotations
and secret references are never returned. Log lines are trimmed, capped and scrubbed of
obvious credentials.
"""
import re
import time
from collections.abc import Callable
from typing import Any

from .clients import KubeReader, LogsReader
from .graph import LOG_FILTER
from .state import K8S_NAME, LOG_GROUP, MAX_WINDOW_MINUTES

MAX_PODS = 20
MAX_EVENTS = 25
MAX_LOG_EVENTS = 50
MAX_LOG_LINES_RETURNED = 20
MAX_MESSAGE_CHARS = 300
LOG_KEYWORDS = ("AccessDenied", "Throttling", "Timeout", "ERROR")
ALLOWED_FILTER_PATTERNS = (LOG_FILTER,)
POD_LABEL = "app.kubernetes.io/name="

_REDACTIONS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"),
)


class ToolInputError(ValueError):
    """Raised for invalid tool input. Messages never echo the rejected value."""


def redact(text: str) -> str:
    for pattern in _REDACTIONS:
        text = pattern.sub("[redacted]", text)
    return text


def _trim(value: Any, limit: int = MAX_MESSAGE_CHARS) -> str:
    return str(value or "")[:limit]


def _safe_text(value: Any, limit: int = MAX_MESSAGE_CHARS) -> str:
    return redact(_trim(value, limit))


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not K8S_NAME.fullmatch(value):
        raise ToolInputError("invalid " + label)
    return value


def _container(status: dict[str, Any]) -> dict[str, Any]:
    state = status.get("state") or {}
    if "waiting" in state:
        current = "waiting: " + _trim((state["waiting"] or {}).get("reason"), 80)
    elif "terminated" in state:
        current = "terminated: " + _trim((state["terminated"] or {}).get("reason"), 80)
    elif "running" in state:
        current = "running"
    else:
        current = "unknown"
    summary: dict[str, Any] = {
        "name": _trim(status.get("name"), 80),
        "ready": bool(status.get("ready")),
        "restarts": _int(status.get("restartCount")),
        "state": current,
    }
    last = (status.get("lastState") or {}).get("terminated") or {}
    if last:
        summary["last_exit"] = {"reason": _trim(last.get("reason"), 80), "exit_code": last.get("exitCode")}
    return summary


def build_tools(kube: KubeReader, logs: LogsReader, clock: Callable[[], float] = time.time) -> dict[str, Callable[..., Any]]:
    def get_pod_status(namespace: str, app: str) -> dict[str, Any]:
        ns, name = _name(namespace, "namespace"), _name(app, "app")
        pods = kube.list_pods(ns, POD_LABEL + name)
        return {
            "pods_found": len(pods),
            "pods": [
                {
                    "name": _trim((pod.get("metadata") or {}).get("name"), 120),
                    "phase": _trim((pod.get("status") or {}).get("phase"), 40),
                    "containers": [_container(c) for c in (pod.get("status") or {}).get("containerStatuses") or []],
                }
                for pod in pods[:MAX_PODS]
            ],
        }

    def get_pod_events(namespace: str, app: str) -> dict[str, Any]:
        ns, name = _name(namespace, "namespace"), _name(app, "app")
        mine = []
        for event in kube.list_events(ns, ""):
            target = (event.get("involvedObject") or {}).get("name") or ""
            if target == name or target.startswith(name + "-"):
                mine.append(event)
        mine.sort(key=lambda e: str(e.get("lastTimestamp") or ""), reverse=True)
        return {
            "events_found": len(mine),
            "events": [
                {
                    "type": _trim(e.get("type"), 20),
                    "reason": _trim(e.get("reason"), 80),
                    "message": _safe_text(e.get("message")),
                    "object": _trim((e.get("involvedObject") or {}).get("kind"), 40)
                    + "/" + _trim((e.get("involvedObject") or {}).get("name"), 120),
                    "count": _int(e.get("count")),
                    "last_seen": _trim(e.get("lastTimestamp"), 40),
                }
                for e in mine[:MAX_EVENTS]
            ],
        }

    def get_deployment_status(namespace: str, name: str) -> dict[str, Any]:
        ns, deployment_name = _name(namespace, "namespace"), _name(name, "name")
        deployment = kube.get_deployment(ns, deployment_name)
        if deployment is None:
            return {"found": False}
        spec, status = deployment.get("spec") or {}, deployment.get("status") or {}
        return {
            "found": True,
            "desired": _int(spec.get("replicas")),
            "ready": _int(status.get("readyReplicas")),
            "updated": _int(status.get("updatedReplicas")),
            "available": _int(status.get("availableReplicas")),
            "conditions": [
                {
                    "type": _trim(c.get("type"), 40),
                    "status": _trim(c.get("status"), 10),
                    "reason": _trim(c.get("reason"), 80),
                    "message": _safe_text(c.get("message")),
                }
                for c in status.get("conditions") or []
            ],
        }

    def search_cloudwatch_logs(log_group: str, filter_pattern: str, window_minutes: int) -> dict[str, Any]:
        if not isinstance(log_group, str) or not LOG_GROUP.fullmatch(log_group):
            raise ToolInputError("invalid log group")
        if filter_pattern not in ALLOWED_FILTER_PATTERNS:
            raise ToolInputError("filter pattern not allowed")
        if isinstance(window_minutes, bool) or not isinstance(window_minutes, int) \
                or not 1 <= window_minutes <= MAX_WINDOW_MINUTES:
            raise ToolInputError("invalid window")
        start_ms = int((clock() - window_minutes * 60) * 1000)
        events = logs.filter_log_events(log_group, filter_pattern, start_ms, MAX_LOG_EVENTS)
        messages = [str(e.get("message") or "") for e in events]
        return {
            "matched": len(events),
            "keyword_counts": {k: sum(1 for m in messages if k in m) for k in LOG_KEYWORDS},
            "lines": [
                {"timestamp": e.get("timestamp"), "message": _safe_text(e.get("message"))}
                for e in events[:MAX_LOG_LINES_RETURNED]
            ],
        }

    return {
        "get_pod_status": get_pod_status,
        "get_pod_events": get_pod_events,
        "get_deployment_status": get_deployment_status,
        "search_cloudwatch_logs": search_cloudwatch_logs,
    }
