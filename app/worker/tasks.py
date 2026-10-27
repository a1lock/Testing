import asyncio
import logging
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.domain.models.job import Job
from app.domain.models.report import Report
from app.services.profile_service import ProfileService
from app.services.validation_pipeline import ValidationPipeline

logger = logging.getLogger(__name__)

# Dedicated engine for worker tasks with NullPool to prevent asyncpg connection
# conflicts across separate asyncio.run() event loops
worker_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)
worker_session_maker = async_sessionmaker(
    bind=worker_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _async_fail_job(job_id: str, error_message: str) -> None:
    """Updates job status to FAILED and records the error message."""
    try:
        async with worker_session_maker() as session:
            job_uuid = uuid.UUID(job_id)
            query = select(Job).where(Job.id == job_uuid)
            result = await session.execute(query)
            job = result.scalar_one_or_none()
            if job:
                job.status = "FAILED"
                job.error_message = error_message
                await session.commit()
                logger.info(f"Job {job_id} successfully transitioned to FAILED")
            else:
                logger.error(f"Job {job_id} not found in database for FAILED update")
    except Exception as e:
        logger.exception(f"Error setting job {job_id} to FAILED: {e}")


async def _async_process_job(job_id: str, file_path: str, profile_id: int | None = None) -> None:
    """Executes the validation workflow inside an async database session."""
    job_uuid = uuid.UUID(job_id)

    async with worker_session_maker() as session:
        # 1. Fetch Job and set status to PROCESSING
        query = select(Job).where(Job.id == job_uuid)
        result = await session.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job with id {job_id} not found")

        job.status = "PROCESSING"
        effective_profile_id = profile_id if profile_id is not None else job.profile_id
        await session.commit()
        logger.info(f"Job {job_id} set to PROCESSING")

        # 2. Retrieve active profile configuration
        profile_config = await ProfileService.get_active_profile_config(
            session=session,
            profile_id=effective_profile_id,
        )

        # 3. Execute validation pipeline
        pipeline = ValidationPipeline()
        is_valid, total_errors, total_warnings, violations_json, stats = pipeline.process_file(
            file_path=file_path,
            profile_config=profile_config,
        )

        # 4. Create or update Report record with payload containing violations and document stats
        violations_payload = {
            "items": violations_json,
            "stats": stats,
        }

        rep_query = select(Report).where(Report.job_id == job_uuid)
        rep_result = await session.execute(rep_query)
        report = rep_result.scalar_one_or_none()

        if report:
            report.is_valid = is_valid
            report.total_errors = total_errors
            report.total_warnings = total_warnings
            report.violations = violations_payload
        else:
            report = Report(
                id=uuid.uuid4(),
                job_id=job_uuid,
                is_valid=is_valid,
                total_errors=total_errors,
                total_warnings=total_warnings,
                violations=violations_payload,
            )
            session.add(report)

        # 5. Mark Job as COMPLETED
        job.status = "COMPLETED"
        await session.commit()
        logger.info(f"Job {job_id} set to COMPLETED (valid={is_valid}, errors={total_errors}, warnings={total_warnings})")


@celery_app.task(name="validate_vkr")
def validate_vkr(job_id: str, file_path: str, profile_id: int | None = None) -> dict:
    """
    Celery task orchestrating end-to-end VKR validation pipeline.

    Args:
        job_id: String UUID of the verification job.
        file_path: Filesystem path to the stored .docx document.
        profile_id: Optional ID of the rule profile to apply.

    Returns:
        dict: Task summary with job_id and status.
    """
    logger.info(f"Celery task validate_vkr started for job {job_id}, file: {file_path}")
    try:
        asyncio.run(_async_process_job(job_id, file_path, profile_id))
        logger.info(f"Validation successfully completed for job {job_id}")
        return {"job_id": job_id, "status": "COMPLETED"}
    except Exception as exc:
        logger.exception(f"Validation failed for job {job_id}: {exc}")
        asyncio.run(_async_fail_job(job_id, str(exc)))
        raise exc
    finally:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted temporary file: {file_path}")
        except Exception as cleanup_exc:
            logger.warning(f"Could not remove temp file {file_path}: {cleanup_exc}")
