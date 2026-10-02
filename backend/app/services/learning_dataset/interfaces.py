from abc import ABC, abstractmethod
from app.services.learning_dataset.models import (
    FeedbackScore,
    LearningDatasetRecord,
    UserEditDelta,
)


class ILearningDataCollector(ABC):
    """Interface thu thập dữ liệu tương tác phục vụ AI Learning và Dataset Benchmarking."""

    @abstractmethod
    def log_generation(self, record: LearningDatasetRecord) -> None:
        """Ghi nhận một lượt sinh nội dung gồm Prompt Knowledge, Input Context, và Generated Content."""
        pass

    @abstractmethod
    def record_user_edit(self, interaction_id: str, delta: UserEditDelta) -> None:
        """Ghi nhận bản chỉnh sửa của người dùng đối với nội dung AI đã sinh."""
        pass

    @abstractmethod
    def record_feedback(self, interaction_id: str, feedback: FeedbackScore) -> None:
        """Ghi nhận điểm đánh giá / phản hồi chất lượng từ người dùng."""
        pass

    @abstractmethod
    def mark_high_quality_example(self, interaction_id: str, is_high_quality: bool = True) -> None:
        """Đánh dấu mẫu nội dung chất lượng cao làm dữ liệu mẫu (Few-shot / Fine-tuning)."""
        pass
