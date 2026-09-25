from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    media_id: str
    message: str = "Image received and stored."