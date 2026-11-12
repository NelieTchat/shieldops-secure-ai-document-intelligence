"""Manual check: one real Bedrock call with SYNTHETIC evidence (sandbox only).

Not part of pytest or CI. Needs AWS credentials, AGENT_MODEL_ID and AGENT_BEDROCK_REGION.
Makes a single model call and prints the report. Never use real incident data here.

    cd agents/incident-investigator && venv/bin/python scripts/live_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from investigator.graph import investigate  # noqa: E402
from investigator.reasoner import make_bedrock_reasoner  # noqa: E402
from investigator.state import ALLOWED_TOOLS  # noqa: E402

SYNTHETIC = {
    "get_deployment_status": {"found": True, "desired": 2, "ready": 0, "updated": 2, "available": 0,
                              "conditions": [{"type": "Available", "status": "False",
                                              "reason": "MinimumReplicasUnavailable", "message": ""}]},
    "get_pod_status": {"pods_found": 2, "pods": [{"name": "api-abc-1", "phase": "Running", "containers": [
        {"name": "api", "ready": False, "restarts": 7, "state": "waiting: CrashLoopBackOff",
         "last_exit": {"reason": "Error", "exit_code": 1}}]}]},
    "get_pod_events": {"events_found": 1, "events": [{"type": "Warning", "reason": "BackOff",
                                                       "message": "Back-off restarting failed container",
                                                       "object": "Pod/api-abc-1", "count": 12, "last_seen": ""}]},
    "search_cloudwatch_logs": {"matched": 3, "keyword_counts": {"AccessDenied": 3, "Throttling": 0,
                                                                "Timeout": 0, "ERROR": 3},
                               "lines": [{"timestamp": 1, "message": "ERROR AccessDenied: s3:GetObject on documents bucket"}]},
}

tools = {name: (lambda name=name, **kwargs: SYNTHETIC[name]) for name in ALLOWED_TOOLS}
state = investigate(
    {"description": "document uploads fail (synthetic exercise)", "namespace": "shieldops-apps",
     "service": "api", "log_group": "/aws/eks/shieldops/api"},
    tools, make_bedrock_reasoner())
print(state["report"])
