"""The only two interfaces the tools may use (ADR 0011, MVP-1).

They are deliberately narrow and read-only: there is no create, patch, delete or exec
method here, so a tool cannot change anything even by mistake. Real implementations
(EKS and CloudWatch Logs) come later and must expose exactly these methods.
Objects are plain dicts shaped like the Kubernetes JSON API.
"""
from typing import Any, Protocol


class KubeReader(Protocol):
    def list_pods(self, namespace: str, label_selector: str) -> list[dict[str, Any]]: ...

    def list_events(self, namespace: str, field_selector: str) -> list[dict[str, Any]]: ...

    def get_deployment(self, namespace: str, name: str) -> dict[str, Any] | None: ...


class LogsReader(Protocol):
    def filter_log_events(
        self, log_group: str, filter_pattern: str, start_time_ms: int, limit: int
    ) -> list[dict[str, Any]]: ...
