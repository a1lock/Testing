import uuid
from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.job import Job


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    total_errors: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_warnings: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    violations: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="report",
    )

