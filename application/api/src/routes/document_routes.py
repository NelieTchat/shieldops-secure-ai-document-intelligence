import logging

from fastapi import APIRouter, Depends, HTTPException

import config
from auth.deps import get_current_user
from models.schemas import CompleteResponse, DocumentCreate, DocumentCreated, DocumentOut
from observability import DOCUMENT_COMPLETIONS, UPLOADS_PREPARED
from services import documents

log = logging.getLogger("api")
router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=DocumentCreated, status_code=201)
def create(body: DocumentCreate, user: dict = Depends(get_current_user)):
    # The owner always comes from the verified token, never from the request body.
    try:
        doc = documents.create_document(user["id"], body.filename, body.size_bytes)
    except ValueError as exc:
        UPLOADS_PREPARED.labels("rejected").inc()
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        upload = documents.presign_upload(doc["object_key"])
    except RuntimeError:
        UPLOADS_PREPARED.labels("not_configured").inc()
        raise HTTPException(status_code=503, detail="Uploads are not configured.")
    except Exception as exc:
        UPLOADS_PREPARED.labels("error").inc()
        log.error("presign failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not prepare the upload.")
    UPLOADS_PREPARED.labels("created").inc()
    return {"id": doc["id"], "filename": doc["filename"], "upload": upload}

@router.post("/{doc_id}/complete", response_model=CompleteResponse, status_code=202)
def complete(doc_id: str, user: dict = Depends(get_current_user)):
    doc = documents.get_owned(user["id"], doc_id)
    if doc is None:
        # Same answer for "does not exist" and "belongs to someone else".
        DOCUMENT_COMPLETIONS.labels("not_found").inc()
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        if not documents.object_exists(doc["object_key"]):
            DOCUMENT_COMPLETIONS.labels("missing_file").inc()
            raise HTTPException(status_code=409, detail="No uploaded file found for this document.")
        if config.SIMULATE_S3_EVENT:
            documents.send_upload_event(doc["object_key"])
            DOCUMENT_COMPLETIONS.labels("queued").inc()
            return {"id": doc["id"], "status": "queued"}
    except HTTPException:
        raise
    except RuntimeError:
        DOCUMENT_COMPLETIONS.labels("not_configured").inc()
        raise HTTPException(status_code=503, detail="Uploads are not configured.")
    except Exception as exc:
        DOCUMENT_COMPLETIONS.labels("error").inc()
        log.error("complete failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not complete the upload.")
    DOCUMENT_COMPLETIONS.labels("uploaded").inc()
    return {"id": doc["id"], "status": "uploaded"}

@router.get("", response_model=list[DocumentOut])
def list_my_documents(user: dict = Depends(get_current_user)):
    return documents.list_documents(user["id"])
