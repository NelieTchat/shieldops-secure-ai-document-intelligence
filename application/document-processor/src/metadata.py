from pydantic import BaseModel, ValidationError

class ProcessingMessage(BaseModel):
    bucket: str
    key: str

def parse_processing_message(raw_json: str) -> ProcessingMessage | None:
    try:
        return ProcessingMessage.model_validate_json(raw_json)
    except ValidationError as e:
        print("Invalid processing message, skipping:", e)
        return None
