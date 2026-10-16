# frontend

Minimal web UI for ShieldOps: register/login, upload .txt documents, watch processing status, and ask questions with cited answers. Plain HTML, CSS and JavaScript served by an unprivileged nginx container. No build step and no npm dependencies. Sandbox/reference code, tested with synthetic data only.

## How it fits together

- nginx serves the static files and proxies `/api/` to the api service (the `/api` prefix is stripped). The page and the API share one origin, so no CORS is needed for API calls.
- Uploads go from the browser straight to S3 using the presigned POST returned by the api. The login token is never sent to S3.
- The JWT is kept in `sessionStorage`, so it is cleared when the tab closes.

## Security choices

- Strict Content-Security-Policy: scripts and styles only from the same origin, no inline code, `connect-src` limited to the same origin and `amazonaws.com`, no framing.
- Also sets `X-Content-Type-Options`, `Referrer-Policy` and `X-Frame-Options`, and hides the nginx version.
- All server text, including model answers and filenames, is inserted with `textContent`, never `innerHTML`, so a malicious document cannot inject markup into the page.
- The container runs as a non-root user and listens on 8080.

## Run locally (sandbox)

Requires the api on port 8001 and the rest of the stack running.

    docker build -t shieldops/frontend:dev application/frontend
    docker run -d --name shieldops-frontend -p 127.0.0.1:8081:8080 shieldops/frontend:dev

Open http://127.0.0.1:8081 (not 8001, which is the api itself).

The sandbox bucket needs a CORS rule allowing POST from http://127.0.0.1:8081 for browser uploads. In the real design this rule belongs in the Terraform S3 module with the real frontend domain.

## Configuration

The proxy target is hard-coded in `nginx.conf` as `host.docker.internal:8001` for local Docker. In Kubernetes it should point at the api Service, and TLS should terminate at the ALB.

## Known limitations

- Token in `sessionStorage` is readable by any script on the page. The strict CSP limits that risk, but short-lived tokens in httpOnly cookies would be stronger.
- No logout on token expiry beyond the next failed request.
- Only .txt uploads. No delete or re-process actions.
- Citations show the file name and section number and are not mapped to the [n] markers in the answer text.
- Hand-written UI, no automated browser tests.
