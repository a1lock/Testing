import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.domain.models.job import Job

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


async def _async_update_job_status(job_id: str, status: str, error_message: str | None = None) -> None:
    async with worker_session_maker() as session:
        try:
            job_uuid = uuid.UUID(job_id)
            query = select(Job).where(Job.id == job_uuid)
            result = await session.execute(query)
            job = result.scalar_one_or_none()
            if job:
                job.status = status
                if error_message is not None:
                    job.error_message = error_message
                await session.commit()
                logger.info(f"Job {job_id} updated to status '{status}'")
            else:
                logger.error(f"Job {job_id} not found in database for status update")
        except Exception as e:
            await session.rollback()
            logger.exception(f"Error updating job {job_id}: {e}")
            raise


async def _async_pipeline(job_id: str, file_path: str) -> None:
    # 1. Transition to PROCESSING
    await _async_update_job_status(job_id, "PROCESSING")

    # 2. Simulate validation workload (5 seconds)
    await asyncio.sleep(5)

    # 3. Transition to COMPLETED
    await _async_update_job_status(job_id, "COMPLETED")


@celery_app.task(name="validate_vkr")
def validate_vkr(job_id: str, file_path: str) -> dict:
    """
    Celery task stub for document validation pipeline.
    Simulates validation work, then marks the job COMPLETED.
    """
    logger.info(f"Starting validate_vkr for job {job_id}, file: {file_path}")
    try:
        asyncio.run(_async_pipeline(job_id, file_path))
        logger.info(f"Validation finished for job {job_id}")
        return {"job_id": job_id, "status": "COMPLETED"}
    except Exception as exc:
        logger.exception(f"Validation failed for job {job_id}: {exc}")
        asyncio.run(_async_update_job_status(job_id, "FAILED", error_message=str(exc)))
        raise exc
