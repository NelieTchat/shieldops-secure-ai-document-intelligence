#!/usr/bin/env bash
# Local security gate: the same two scans CI runs, with the same pinned images.
# Usage: commit your change, run scripts/check.sh, push only if it passes.
# Gitleaks scans committed history, so run it after committing. Needs Docker.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TRIVY="ghcr.io/aquasecurity/trivy@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222"
GITLEAKS="ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT
STATUS=0

echo "== gitleaks (full committed history) =="
docker run --rm -v "$REPO:/repo" "$GITLEAKS" detect --source /repo --redact --no-banner -v > "$OUT" 2>&1
if [ $? -eq 0 ]
then
  echo "PASS: no leaks found"
else
  STATUS=1
  echo "FAIL:"
  grep -E "RuleID|File|Line|Commit|Fingerprint|leaks found" "$OUT"
fi

echo "== trivy (vulnerabilities and misconfigurations, HIGH and CRITICAL) =="
docker run --rm -v "$REPO:/repo" "$TRIVY" fs --scanners vuln,misconfig --severity HIGH,CRITICAL \
  --exit-code 1 --ignorefile /repo/.trivyignore.yaml --quiet /repo > "$OUT" 2>&1
if [ $? -eq 0 ]
then
  echo "PASS: clean"
else
  STATUS=1
  echo "FAIL:"
  tail -25 "$OUT"
fi

if [ "$STATUS" -eq 0 ]
then
  echo "GATE: PASS"
else
  echo "GATE: FAIL"
fi
exit "$STATUS"
