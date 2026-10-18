from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobCreateResponse(BaseModel):
    job_id: UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

