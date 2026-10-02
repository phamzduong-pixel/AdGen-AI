from datetime import date

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_conversations: int
    total_generated_contents: int
    total_saved_contents: int
    total_evaluations: int
    total_variants: int
    top_platform: str | None
    contents_last_7_days: int
    contents_last_30_days: int


class DailyActivity(BaseModel):
    date: date
    count: int


class DashboardActivity(BaseModel):
    days: list[DailyActivity]


class PlatformUsage(BaseModel):
    platform: str
    count: int
    percentage: float
    average_score: float | None = None


class DashboardPlatformUsage(BaseModel):
    platforms: list[PlatformUsage]
