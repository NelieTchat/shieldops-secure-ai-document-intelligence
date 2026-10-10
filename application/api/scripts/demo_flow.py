"""End-to-end check against a running stack (sandbox, synthetic data only).

Usage: python scripts/demo_flow.py [base_url]
"""
import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
PASSWORD = "a-long-demo-password-123"
DOC_TEXT = (
    "Harbor Logistics demo document (synthetic). "
    "The Harbor warehouse ships orders every Thursday at 2pm. "
    "Returns are accepted within 30 days."
)
QUESTION = "When does the Harbor warehouse ship orders?"

results = []

def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

def main():
    suffix = uuid.uuid4().hex[:8]
    users = {"alice": f"alice_{suffix}", "bob": f"bob_{suffix}"}
    with httpx.Client(base_url=BASE, timeout=120) as client:
        tokens = {}
        for name, username in users.items():
            client.post("/auth/register",
                        json={"username": username, "password": PASSWORD}).raise_for_status()
            response = client.post("/auth/login",
                                   json={"username": username, "password": PASSWORD})
            response.raise_for_status()
            tokens[name] = response.json()["access_token"]

        def auth(name):
            return {"Authorization": f"Bearer {tokens[name]}"}

        data = DOC_TEXT.encode()
        response = client.post("/documents", headers=auth("alice"),
                               json={"filename": "harbor.txt", "size_bytes": len(data)})
        response.raise_for_status()
        doc = response.json()
        upload = doc["upload"]
        response = httpx.post(upload["url"], data=upload["fields"],
                              files={"file": ("harbor.txt", data)}, timeout=60)
        check("alice uploads to S3 with the presigned form", response.status_code == 204,
              f"status {response.status_code}")
        response = client.post(f"/documents/{doc['id']}/complete", headers=auth("alice"))
        check("alice completes the upload", response.status_code == 202,
              f"status {response.status_code}")

        print("waiting for the pipeline (ingestion -> processing -> embeddings)...")
        status = "?"
        deadline = time.time() + 150
        while time.time() < deadline:
            listing = client.get("/documents", headers=auth("alice")).json()
            status = listing[0]["status"] if listing else "?"
            print("  status:", status)
            if status == "processed":
                break
            time.sleep(5)
        check("document reaches 'processed'", status == "processed", f"last status {status}")

        alice = client.post("/query", headers=auth("alice"),
                            json={"question": QUESTION, "top_k": 3})
        body = alice.json() if alice.status_code == 200 else {}
        print("\nalice's answer:", body.get("answer"))
        check("alice gets an answer mentioning Thursday",
              alice.status_code == 200 and "thursday" in body.get("answer", "").lower(),
              f"status {alice.status_code}")
        check("alice's citations point at her own folder",
              bool(body.get("citations"))
              and all("/" in c["key"] and c["key"].split("/")[1] == doc["upload"]["fields"]["key"].split("/")[1]
                      for c in body["citations"]))

        bob = client.post("/query", headers=auth("bob"),
                          json={"question": QUESTION, "top_k": 3})
        bob_body = bob.json() if bob.status_code == 200 else {}
        print("bob's answer:  ", bob_body.get("answer"))
        check("bob retrieves nothing of alice's",
              bob.status_code == 200 and bob_body.get("chunks_retrieved") == 0
              and bob_body.get("citations") == [],
              f"status {bob.status_code}")
        check("bob's document list is empty",
              client.get("/documents", headers=auth("bob")).json() == [])
        check("bob cannot complete alice's document (404)",
              client.post(f"/documents/{doc['id']}/complete", headers=auth("bob")).status_code == 404)
        check("no token is rejected (401)", client.get("/documents").status_code == 401)

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

main()
