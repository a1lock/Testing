import hashlib
import os
import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.api.schemas.job import JobCreateResponse, JobStatusResponse
from app.core.config import settings
from app.domain.models.job import Job
from app.worker.tasks import validate_vkr

router = APIRouter()


@router.post(
    "/",
    response_model=JobCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new VKR verification job",
)
async def create_job(
    file: UploadFile = File(...),
    profile_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> JobCreateResponse:
    # 1. Ensure storage directory exists and save uploaded file with unique name
    os.makedirs(settings.TEMP_STORAGE_PATH, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}_{file.filename or 'document.docx'}"
    file_path = os.path.join(settings.TEMP_STORAGE_PATH, unique_filename)

    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    file_hash = hashlib.sha256(file_content).hexdigest()

    # 2. Create Job record in DB with PENDING status and explicit UUID
    new_job = Job(
        id=uuid.uuid4(),
        status="PENDING",
        profile_id=profile_id,
        file_hash=file_hash,
    )
    db.add(new_job)

    # 3. Commit to persist record
    await db.commit()
    await db.refresh(new_job)

    # 4. Enqueue background Celery task
    validate_vkr.delay(str(new_job.id), file_path, profile_id)

    # 5. Return creation response
    return JobCreateResponse(
        job_id=new_job.id,
        status=new_job.status,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get status of VKR verification job",
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        error_message=job.error_message,
    )

