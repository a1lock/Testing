from typing import Any, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_db
from app.api.schemas.report import DocumentStatsSchema, ReportResponse, ViolationSchema
from app.domain.models.job import Job
from app.domain.models.report import Report

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=Union[ReportResponse, dict[str, Any]],
    responses={
        200: {
            "description": "Validation completed successfully or job failed",
            "model": ReportResponse,
        },
        202: {
            "description": "Validation in progress",
            "content": {
                "application/json": {
                    "example": {
                        "status": "PROCESSING",
                        "message": "Проверка еще выполняется",
                    }
                }
            },
        },
        404: {
            "description": "Job or report not found",
        },
    },
    summary="Get VKR verification report",
)
async def get_report(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Retrieve verification report by job UUID.

    - Returns 404 if the job is not found.
    - Returns 202 if the job is currently PENDING or PROCESSING.
    - Returns 200 with error details if the job FAILED.
    - Returns 200 with ReportResponse schema if validation completed.
    """
    query = select(Job).options(selectinload(Job.report)).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )

    if job.status in ("PENDING", "PROCESSING"):
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": job.status,
                "message": "Проверка еще выполняется",
            },
        )

    if job.status == "FAILED":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "FAILED",
                "error": job.error_message,
            },
        )

    report = job.report
    if not report:
        # Fallback direct lookup by job_id
        rep_query = select(Report).where(Report.job_id == job_id)
        rep_result = await db.execute(rep_query)
        report = rep_result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for completed job {job_id} not found",
        )

    summary_text = (
        "Документ успешно прошел проверку нормоконтроля."
        if report.is_valid
        else f"Обнаружено нарушений: {report.total_errors} критических ошибок, {report.total_warnings} предупреждений."
    )

    if isinstance(report.violations, dict):
        raw_violations = report.violations.get("items", [])
        raw_stats = report.violations.get("stats")
    else:
        raw_violations = report.violations or []
        raw_stats = None

    stats_schema = (
        DocumentStatsSchema(**raw_stats)
        if isinstance(raw_stats, dict)
        else DocumentStatsSchema(
            total_paragraphs=0,
            total_tables=0,
            total_sections=1,
        )
    )

    violations_schemas = [
        ViolationSchema.model_validate(v) for v in raw_violations
    ]

    return ReportResponse(
        job_id=str(job.id),
        filename="document.docx",
        is_valid=report.is_valid,
        summary=summary_text,
        total_errors=report.total_errors,
        total_warnings=report.total_warnings,
        stats=stats_schema,
        violations=violations_schemas,
    )
