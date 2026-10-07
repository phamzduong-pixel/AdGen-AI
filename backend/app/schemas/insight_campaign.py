from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AdvertisingBriefResponse(BaseModel):
    id: int
    owner_user_id: int
    advertising_angle_id: int
    title: str
    objective: str | None
    target_audience: str | None
    core_message: str
    copy_direction: str
    rationale: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignMetricSnapshotCreate(BaseModel):
    metric_payload: dict[str, Any] = Field(min_length=1)
    captured_at: datetime | None = None
    metric_schema: str = Field(default="campaign_metrics_v1", min_length=1, max_length=80)

    @field_validator("captured_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Thời điểm ghi nhận phải có múi giờ")
        return value


class CampaignMetricSnapshotResponse(BaseModel):
    id: int
    owner_user_id: int
    campaign_id: int
    advertising_brief_id: int | None
    captured_at: datetime
    metric_schema: str
    metric_payload: dict[str, Any]
    created_at: datetime
