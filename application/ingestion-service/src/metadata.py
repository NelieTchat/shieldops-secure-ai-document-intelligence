from pydantic import BaseModel, ValidationError


class S3Object(BaseModel):
    key: str


class S3Bucket(BaseModel):
    name: str


class S3Detail(BaseModel):
    bucket: S3Bucket
    object: S3Object


class UploadEvent(BaseModel):
    detail: S3Detail


def parse_upload_event(raw_json: str) -> UploadEvent | None:
    """
    Takes the raw message body (a JSON string) and validates it against
    the expected S3-upload-event shape. Returns None (and prints why)
    if it doesn't match, instead of crashing the whole service.
    """
    try:
        return UploadEvent.model_validate_json(raw_json)
    except ValidationError as e:
        print("Invalid message, skipping:", e)
        return None
