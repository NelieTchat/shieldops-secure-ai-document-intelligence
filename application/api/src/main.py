from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

import config
from db import ensure_tables
from routes import auth_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.require_jwt_secret()  # refuse to start with a missing or weak secret
    ensure_tables()
    yield

app = FastAPI(title="ShieldOps API", lifespan=lifespan)
app.include_router(auth_routes.router)

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT)
