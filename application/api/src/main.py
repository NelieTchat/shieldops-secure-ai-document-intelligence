import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

import config
from db import ensure_tables
from observability import RequestObservabilityMiddleware, configure_logging, start_metrics_server
from routes import auth_routes, document_routes, query_routes

configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.require_jwt_secret()  # refuse to start with a missing or weak secret
    config.require_db_config()  # refuse to start without explicit database settings
    ensure_tables()
    yield

app = FastAPI(title="ShieldOps API", lifespan=lifespan)
app.add_middleware(RequestObservabilityMiddleware)
app.include_router(auth_routes.router)
app.include_router(document_routes.router)
app.include_router(query_routes.router)

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    start_metrics_server(config.METRICS_HOST, config.METRICS_PORT)
    # access_log off: uvicorn's access log prints full URLs (document IDs, query strings).
    # The request middleware logs a safe, structured line instead.
    uvicorn.run(app, host=config.HOST, port=config.PORT, access_log=False, log_config=None)
