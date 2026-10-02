from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class DatasetType(str, Enum):
    EVALUATION = "evaluation"
    RECOMMENDATION = "recommendation"
    PERSONALIZATION = "personalization"
    FINE_TUNING = "fine_tuning"


@dataclass
class FeedbackScore:
    rating: int  # 1 to 5
    is_positive: bool
    review_comments: str | None = None


@dataclass
class UserEditDelta:
    original_text: str
    edited_text: str
    change_ratio: float  # 0.0 (identical) to 1.0 (completely rewritten)
    added_length: int = 0
    removed_length: int = 0


@dataclass
class LearningDatasetRecord:
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prompt_knowledge: dict[str, Any] = field(default_factory=dict)
    input_context: dict[str, Any] = field(default_factory=dict)
    generated_content: str = ""
    user_edits: UserEditDelta | None = None
    user_feedback: FeedbackScore | None = None
    is_high_quality_example: bool = False
    eligible_dataset_types: list[DatasetType] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
