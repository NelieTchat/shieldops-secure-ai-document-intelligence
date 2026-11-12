import json

import pytest

from investigator.clients import KubeReader, LogsReader
from investigator.graph import LOG_FILTER, investigate
from investigator.state import ALLOWED_TOOLS
from investigator.tools import MAX_EVENTS, MAX_LOG_LINES_RETURNED, MAX_PODS, ToolInputError, build_tools

NOW = 1_000_000.0


class FakeKube:
    def __init__(self, pods=None, events=None, deployment=None):
        self.pods, self.events, self.deployment, self.calls = pods or [], events or [], deployment, []

    def list_pods(self, namespace, label_selector):
        self.calls.append(("list_pods", namespace, label_selector))
        return self.pods

    def list_events(self, namespace, field_selector):
        self.calls.append(("list_events", namespace, field_selector))
        return self.events

    def get_deployment(self, namespace, name):
        self.calls.append(("get_deployment", namespace, name))
        return self.deployment


class FakeLogs:
    def __init__(self, events=None):
        self.events, self.calls = events or [], []

    def filter_log_events(self, log_group, filter_pattern, start_time_ms, limit):
        self.calls.append((log_group, filter_pattern, start_time_ms, limit))
        return self.events


def crashing_pod(name="api-abc-1"):
    return {
        "metadata": {"name": name},
        "spec": {"containers": [{"env": [{"name": "DB_PASSWORD", "value": "hunter2"}]}]},
        "status": {
            "phase": "Running",
            "containerStatuses": [{
                "name": "api", "ready": False, "restartCount": 7,
                "state": {"waiting": {"reason": "CrashLoopBackOff", "message": "back-off"}},
                "lastState": {"terminated": {"reason": "Error", "exitCode": 1}},
            }],
        },
    }


def tools_for(kube=None, logs=None):
    return build_tools(kube or FakeKube(), logs or FakeLogs(), clock=lambda: NOW)


def test_pod_status_returns_a_safe_subset_and_never_the_spec():
    kube = FakeKube(pods=[crashing_pod()])
    result = tools_for(kube)["get_pod_status"](namespace="shieldops-apps", app="api")
    assert "hunter2" not in json.dumps(result) and "DB_PASSWORD" not in json.dumps(result)
    container = result["pods"][0]["containers"][0]
    assert container["state"] == "waiting: CrashLoopBackOff"
    assert container["restarts"] == 7
    assert container["last_exit"] == {"reason": "Error", "exit_code": 1}
    assert kube.calls == [("list_pods", "shieldops-apps", "app.kubernetes.io/name=api")]


def test_the_number_of_pods_returned_is_capped():
    kube = FakeKube(pods=[crashing_pod("api-" + str(i)) for i in range(50)])
    result = tools_for(kube)["get_pod_status"](namespace="shieldops-apps", app="api")
    assert result["pods_found"] == 50 and len(result["pods"]) == MAX_PODS


def test_events_are_filtered_to_the_app_newest_first_capped_and_scrubbed():
    events = [{"type": "Warning", "reason": "BackOff", "message": "x" * 1000,
               "involvedObject": {"kind": "Pod", "name": "api-abc-" + str(i)},
               "count": 3, "lastTimestamp": "2026-11-11T10:%02d:00Z" % i} for i in range(40)]
    events.append({"type": "Normal", "reason": "Pulled", "message": "other",
                   "involvedObject": {"kind": "Pod", "name": "llm-service-1"}, "lastTimestamp": "2026-11-11T11:00:00Z"})
    events.append({"type": "Warning", "reason": "Failed", "message": "token Bearer abc.def.ghi leaked",
                   "involvedObject": {"kind": "Pod", "name": "api-zzz"}, "lastTimestamp": "2026-11-11T09:00:00Z"})
    result = tools_for(FakeKube(events=events))["get_pod_events"](namespace="shieldops-apps", app="api")
    assert result["events_found"] == 41 and len(result["events"]) == MAX_EVENTS
    assert result["events"][0]["last_seen"] == "2026-11-11T10:39:00Z"
    assert all("llm-service" not in e["object"] for e in result["events"])
    assert all(len(e["message"]) <= 300 for e in result["events"])
    only_one = tools_for(FakeKube(events=events[-1:]))["get_pod_events"](namespace="shieldops-apps", app="api")
    assert "Bearer" not in only_one["events"][0]["message"] and "[redacted]" in only_one["events"][0]["message"]


def test_deployment_status_reports_replicas_and_conditions():
    deployment = {"spec": {"replicas": 2, "template": {"spec": {"secret": "ignored"}}},
                  "status": {"readyReplicas": 0, "updatedReplicas": 2, "availableReplicas": 0,
                             "conditions": [{"type": "Available", "status": "False", "reason": "MinimumReplicasUnavailable",
                                             "message": "no replicas"}]}}
    result = tools_for(FakeKube(deployment=deployment))["get_deployment_status"](namespace="shieldops-apps", name="api")
    assert result["desired"] == 2 and result["ready"] == 0
    assert result["conditions"][0]["reason"] == "MinimumReplicasUnavailable"
    assert "ignored" not in json.dumps(result)


def test_a_missing_deployment_is_reported_as_not_found():
    result = tools_for(FakeKube())["get_deployment_status"](namespace="shieldops-apps", name="api")
    assert result == {"found": False}


def test_log_search_counts_keywords_caps_lines_and_scrubs_credentials():
    events = [{"timestamp": i, "message": "AccessDenied for AKIAABCDEFGHIJKLMNOP " + str(i)} for i in range(30)]
    events.append({"timestamp": 99, "message": "ERROR Bearer abcdef.ghijkl auth failed"})
    events.append({"timestamp": 100, "message": "Timeout eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk"})
    logs = FakeLogs(events)
    result = tools_for(logs=logs)["search_cloudwatch_logs"](
        log_group="/aws/eks/shieldops/api", filter_pattern=LOG_FILTER, window_minutes=30)
    assert logs.calls[0][2] == int((NOW - 30 * 60) * 1000)
    assert result["matched"] == 32 and len(result["lines"]) == MAX_LOG_LINES_RETURNED
    assert result["keyword_counts"]["AccessDenied"] == 30
    assert result["keyword_counts"]["ERROR"] == 1 and result["keyword_counts"]["Timeout"] == 1
    text = json.dumps(result)
    assert "AKIA" not in text and "Bearer" not in text and "eyJ" not in text


@pytest.mark.parametrize("arguments", [
    {"log_group": "bad group", "filter_pattern": LOG_FILTER, "window_minutes": 30},
    {"log_group": "/aws/x", "filter_pattern": "?ERROR ?password", "window_minutes": 30},
    {"log_group": "/aws/x", "filter_pattern": LOG_FILTER, "window_minutes": 0},
    {"log_group": "/aws/x", "filter_pattern": LOG_FILTER, "window_minutes": 999},
    {"log_group": "/aws/x", "filter_pattern": LOG_FILTER, "window_minutes": True},
])
def test_invalid_log_search_input_is_rejected_before_any_call(arguments):
    logs = FakeLogs()
    with pytest.raises(ToolInputError):
        tools_for(logs=logs)["search_cloudwatch_logs"](**arguments)
    assert logs.calls == []


@pytest.mark.parametrize("name", ["Bad_NS", "x; kubectl delete pod y", "", "a" * 64])
def test_invalid_kubernetes_names_are_rejected_before_any_call(name):
    kube = FakeKube()
    tools = tools_for(kube)
    for call in (lambda: tools["get_pod_status"](namespace=name, app="api"),
                 lambda: tools["get_pod_events"](namespace="shieldops-apps", app=name),
                 lambda: tools["get_deployment_status"](namespace=name, name="api")):
        with pytest.raises(ToolInputError):
            call()
    assert kube.calls == []


def test_the_tool_set_matches_the_allowlist_exactly():
    assert set(tools_for()) == set(ALLOWED_TOOLS)


def test_the_client_interfaces_contain_only_read_methods():
    kube_methods = {n for n in vars(KubeReader) if not n.startswith("_")}
    logs_methods = {n for n in vars(LogsReader) if not n.startswith("_")}
    assert kube_methods == {"list_pods", "list_events", "get_deployment"}
    assert logs_methods == {"filter_log_events"}


def test_the_whole_investigation_runs_end_to_end_on_the_fake_clients():
    kube = FakeKube(pods=[crashing_pod()],
                    deployment={"spec": {"replicas": 2}, "status": {"readyReplicas": 0}})
    logs = FakeLogs([{"timestamp": 1, "message": "AccessDenied s3:GetObject"}])
    seen = []

    def reasoner(incident, evidence):
        seen.append([item["tool"] for item in evidence if item["ok"]])
        return {"summary": "Pods crash looping.", "likely_cause": "Missing S3 permission.",
                "confidence": "medium", "evidence_refs": [1, 3]}

    state = investigate(
        {"description": "uploads fail", "namespace": "shieldops-apps", "service": "api",
         "log_group": "/aws/eks/shieldops/api"},
        build_tools(kube, logs, clock=lambda: NOW), reasoner)
    assert len(seen[0]) == 4
    assert "CrashLoopBackOff" in state["report"] and "hunter2" not in state["report"]
    assert {call[0] for call in kube.calls} <= {"list_pods", "list_events", "get_deployment"}
