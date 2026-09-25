from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.routes.messages import get_current_session
from schemas.image import ImageUploadResponse
from services.image_service import (
    ImageService,
    ImageTooLargeError,
    ImageValidationError,
)

router = APIRouter()


def get_image_service(request: Request) -> ImageService:
    return request.app.state.image_service


@router.post("/sessions/{session_id}/images", response_model=ImageUploadResponse)
async def upload_image(
    session_id: str,
    file: UploadFile,
    request: Request,
    current_session: str = Depends(get_current_session),
    image_service: ImageService = Depends(get_image_service),
) -> ImageUploadResponse:
    if session_id != current_session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not match the access token.",
        )

    await request.app.state.rate_limiter.check_image(session_id)
    try:
        await image_service.validate(file)
        file_bytes = await file.read()
        await file.seek(0)
    except ImageTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not await image_service.safety_scan(file_bytes, file.content_type or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image did not pass the safety scan.",
        )

    media_id = await image_service.store(file_bytes, file.content_type or "")
    await request.app.state.session_store.touch(session_id)
    return ImageUploadResponse(media_id=media_id)