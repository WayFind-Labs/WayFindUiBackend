from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from app.routes.images import upload_image
from app.config import Settings
from services.image_service import ImageService, ImageTooLargeError, ImageValidationError


class FakeLimiter:
    async def check_image(self, _session_id: str) -> None:
        return None


class FakeStore:
    async def touch(self, _session_id: str) -> None:
        return None


def upload(name: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(BytesIO(content), filename=name, headers={"content-type": content_type})


@pytest.mark.asyncio
async def test_valid_jpeg_returns_media_id() -> None:
    service = ImageService(Settings())
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(rate_limiter=FakeLimiter(), session_store=FakeStore()))
    )

    response = await upload_image(
        "session-1",
        upload("photo.jpg", b"\xff\xd8\xfffake", "image/jpeg"),
        request,
        current_session="session-1",
        image_service=service,
    )

    assert response.media_id


@pytest.mark.asyncio
async def test_oversized_image_is_rejected() -> None:
    service = ImageService(Settings(max_image_size_mb=0))
    file = upload("photo.jpg", b"\xff\xd8\xff", "image/jpeg")

    with pytest.raises(ImageTooLargeError):
        await service.validate(file)


@pytest.mark.asyncio
async def test_invalid_image_type_is_rejected() -> None:
    service = ImageService(Settings())
    file = upload("photo.txt", b"not-an-image", "text/plain")

    with pytest.raises(ImageValidationError):
        await service.validate(file)