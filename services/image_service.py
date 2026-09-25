from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings, get_settings


class ImageValidationError(Exception):
    """Raised when an uploaded file is not an allowed image."""


class ImageService:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._max_size_bytes = settings.max_image_size_mb * 1024 * 1024
        self._allowed_types = set(settings.allowed_image_types)

    async def validate(self, file: UploadFile) -> None:
        if file.content_type not in self._allowed_types:
            raise ImageValidationError("Unsupported image type.")

        file_bytes = await file.read(self._max_size_bytes + 1)
        await file.seek(0)
        if len(file_bytes) > self._max_size_bytes:
            raise ImageValidationError("Image exceeds the maximum allowed size.")
        if not self._has_valid_signature(file_bytes, file.content_type):
            raise ImageValidationError("Uploaded file is not a valid image.")

    @staticmethod
    def _has_valid_signature(file_bytes: bytes, mime_type: str | None) -> bool:
        if mime_type == "image/jpeg":
            return file_bytes.startswith(b"\xff\xd8\xff")
        if mime_type == "image/png":
            return file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        if mime_type == "image/webp":
            return (
                len(file_bytes) >= 12
                and file_bytes.startswith(b"RIFF")
                and file_bytes[8:12] == b"WEBP"
            )
        return False

    async def safety_scan(self, file_bytes: bytes, mime_type: str) -> bool:
        """Development stub; production will call the configured scan service."""
        return bool(file_bytes and mime_type in self._allowed_types)

    async def store(self, file_bytes: bytes, mime_type: str) -> str:
        """Development stub; production will store bytes in object storage."""
        return str(uuid4())