# Incident Investigator (ADR 0011, MVP-1)

A read-only agent that investigates an incident in the ShieldOps platform. This is step 1
of the build order in ADR 0011: the LangGraph state machine, built and tested locally.

Scope of this step: the graph, input validation, evidence limits and the report. The four
real tools (step 2) and the Bedrock reasoner (step 3) are injected and replaced by stubs
in the tests, so everything here runs offline.

Principle from the ADR: the model never receives infrastructure authority. In this code
that means the reasoner only returns a diagnosis; tools are an allowlist of four read-only
functions, capped at 8 calls and a fixed output size; and a failing tool or reasoner is
recorded by exception type only.

Graph: make_plan -> gather_evidence -> (reason_over_evidence) -> write_report.
If no tool returns usable evidence, the model is skipped and the report says so.

## Tools (ADR 0011 step 2)

`get_pod_status`, `get_pod_events`, `get_deployment_status` and `search_cloudwatch_logs`
live in `src/investigator/tools.py`. They talk only to the two read-only interfaces in
`clients.py`, validate every argument, and return a safe subset of fields: never pod
specs, environment variables, annotations or secret references. Log lines are trimmed,
capped and scrubbed of obvious credentials. Real EKS and CloudWatch clients come later and
must implement exactly those interfaces.

## Run the tests

    cd agents/incident-investigator
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements-dev.txt
    pytest
