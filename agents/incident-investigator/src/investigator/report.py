"""Deterministic markdown report. Nothing here calls a tool or a model."""
import re


def _clean(text: str, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def render_report(state) -> str:
    incident = state["incident"]
    lines = [
        "# Incident investigation",
        "",
        "_Read-only investigation. No actions were taken._",
        "",
        "**Service:** " + incident["service"] + " (namespace " + incident["namespace"] + ")",
        "**Reported:** " + _clean(incident["description"]),
        "",
        "## Evidence",
        "",
    ]
    if not state["evidence"]:
        lines += ["No evidence was collected.", ""]
    for index, item in enumerate(state["evidence"]):
        lines.append("### [" + str(index) + "] " + item["tool"] + " (" + ("ok" if item["ok"] else "failed") + ")")
        lines.append("")
        for text_line in item["result"].splitlines() or [""]:
            lines.append("    " + text_line)
        lines.append("")
    lines += ["## Diagnosis", ""]
    diagnosis = state["diagnosis"]
    if state["reasoning_failed"]:
        lines.append("The reasoning step failed. The evidence above is still valid. Confidence: low.")
    elif diagnosis is None:
        lines.append("Insufficient evidence: no tool returned usable data. Confidence: low.")
    else:
        lines += [
            "**Summary:** " + _clean(diagnosis["summary"], 2000),
            "",
            "**Likely cause:** " + _clean(diagnosis["likely_cause"], 2000),
            "",
            "**Confidence:** " + diagnosis["confidence"],
            "",
            "**Evidence used:** " + (", ".join("[" + str(i) + "]" for i in diagnosis["evidence_refs"]) or "none"),
        ]
    lines.append("")
    return "\n".join(lines)
