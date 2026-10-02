import json
from pathlib import Path
import threading
from typing import Any

from app.services.learning_dataset.interfaces import ILearningDataCollector
from app.services.learning_dataset.models import (
    DatasetType,
    FeedbackScore,
    LearningDatasetRecord,
    UserEditDelta,
)

DEFAULT_STORAGE_FILE = (
    Path(__file__).resolve().parent.parent.parent / "data" / "learning_dataset.jsonl"
)


class LearningDatasetService(ILearningDataCollector):
    """
    Hệ thống thu thập dữ liệu phục vụ AI Learning, Evaluation & Fine-tuning Dataset:
    Thu thập có cấu trúc 5 thành phần:
    1. Prompt Knowledge (System prompt, Platform intelligence, Marketing rules)
    2. Input Context (Product, Audience, Campaign Objective, Platform)
    3. Generated Content (Nội dung thô do AI sinh ra)
    4. User Edits (Bản chỉnh sửa cuối cùng của người dùng + độ lệch)
    5. User Feedback & High-quality Examples (Đánh giá chất lượng thực tế)

    Phân loại có chọn lọc thành 4 loại Dataset:
    - EVALUATION: Đánh giá benchmark chất lượng và độ tuân thủ luật nền tảng.
    - RECOMMENDATION: Học góc tiếp cận / mẫu ưa chuộng.
    - PERSONALIZATION: Học phong cách thương hiệu / giọng văn cá nhân.
    - FINE_TUNING: Bộ dữ liệu tinh chỉnh có chất lượng cao nhất (Rating >= 4 sao hoặc User Edit chuẩn).
    """

    def __init__(self, storage_path: Path | None = None):
        self._records: dict[str, LearningDatasetRecord] = {}
        self._lock = threading.Lock()
        self._storage_path = storage_path
        if self._storage_path and self._storage_path.is_file():
            self._load_from_storage()

    def _persist(self) -> None:
        if not self._storage_path:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            content = self.export_to_jsonl(list(self._records.values()))
            self._storage_path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def _load_from_storage(self) -> None:
        if not self._storage_path or not self._storage_path.is_file():
            return
        try:
            for line in self._storage_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                user_edits = None
                if "user_edits" in data and data["user_edits"]:
                    user_edits = UserEditDelta(
                        original_text=data["user_edits"].get("original_text", ""),
                        edited_text=data["user_edits"].get("edited_text", ""),
                        change_ratio=data["user_edits"].get("change_ratio", 0.0),
                    )
                user_feedback = None
                if "user_feedback" in data and data["user_feedback"]:
                    user_feedback = FeedbackScore(
                        rating=data["user_feedback"].get("rating", 5),
                        is_positive=data["user_feedback"].get("is_positive", True),
                        review_comments=data["user_feedback"].get("review_comments", ""),
                    )
                rec = LearningDatasetRecord(
                    interaction_id=data.get("interaction_id", ""),
                    prompt_knowledge=data.get("prompt_knowledge", {}),
                    input_context=data.get("input_context", {}),
                    generated_content=data.get("generated_content", ""),
                    user_edits=user_edits,
                    user_feedback=user_feedback,
                    is_high_quality_example=data.get("is_high_quality_example", False),
                    tags=data.get("tags", []),
                )
                self._update_dataset_eligibility(rec)
                self._records[rec.interaction_id] = rec
        except Exception:
            pass

    def _update_dataset_eligibility(self, record: LearningDatasetRecord) -> None:
        types = [DatasetType.EVALUATION]

        # Recommendation candidate
        if record.is_high_quality_example or (record.user_feedback and record.user_feedback.is_positive):
            types.append(DatasetType.RECOMMENDATION)

        # Personalization candidate
        if record.input_context.get("brand_id") or record.input_context.get("brand_name"):
            types.append(DatasetType.PERSONALIZATION)

        # Fine-tuning candidate: Only high quality with positive rating or complete edited text
        if record.is_high_quality_example:
            if record.user_feedback and record.user_feedback.rating >= 4:
                types.append(DatasetType.FINE_TUNING)
            elif record.user_edits and record.user_edits.change_ratio < 0.8:
                types.append(DatasetType.FINE_TUNING)

        record.eligible_dataset_types = list(set(types))

    def log_generation(self, record: LearningDatasetRecord) -> None:
        with self._lock:
            self._update_dataset_eligibility(record)
            self._records[record.interaction_id] = record
            self._persist()

    def record_user_edit(self, interaction_id: str, delta: UserEditDelta) -> None:
        with self._lock:
            record = self._records.get(interaction_id)
            if record:
                record.user_edits = delta
                self._update_dataset_eligibility(record)
                self._persist()

    def record_feedback(self, interaction_id: str, feedback: FeedbackScore) -> None:
        with self._lock:
            record = self._records.get(interaction_id)
            if record:
                record.user_feedback = feedback
                if feedback.rating >= 4 or feedback.is_positive:
                    record.is_high_quality_example = True
                self._update_dataset_eligibility(record)
                self._persist()

    def mark_high_quality_example(self, interaction_id: str, is_high_quality: bool = True) -> None:
        with self._lock:
            record = self._records.get(interaction_id)
            if record:
                record.is_high_quality_example = is_high_quality
                self._update_dataset_eligibility(record)
                self._persist()

    def get_record(self, interaction_id: str) -> LearningDatasetRecord | None:
        with self._lock:
            return self._records.get(interaction_id)

    def query_dataset(
        self,
        dataset_type: DatasetType | None = None,
        platform: str | None = None,
        only_high_quality: bool = False,
        min_rating: int | None = None,
        limit: int = 100,
    ) -> list[LearningDatasetRecord]:
        with self._lock:
            results = []
            for r in self._records.values():
                if dataset_type and dataset_type not in r.eligible_dataset_types:
                    continue
                if platform:
                    rec_plat = r.input_context.get("platform", "").lower()
                    if rec_plat != platform.lower():
                        continue
                if only_high_quality and not r.is_high_quality_example:
                    continue
                if min_rating is not None:
                    if not r.user_feedback or r.user_feedback.rating < min_rating:
                        continue
                results.append(r)
            return results[:limit]

    def export_to_jsonl(
        self,
        records: list[LearningDatasetRecord],
        target_dataset_type: DatasetType | None = None,
    ) -> str:
        """Xuất danh sách bản ghi ra định dạng JSON Lines tiêu chuẩn cho dataset training/eval."""
        lines = []
        for r in records:
            if target_dataset_type and target_dataset_type not in r.eligible_dataset_types:
                continue

            obj: dict[str, Any] = {
                "interaction_id": r.interaction_id,
                "timestamp": r.timestamp.isoformat(),
                "eligible_datasets": [d.value for d in r.eligible_dataset_types],
                "prompt_knowledge": r.prompt_knowledge,
                "input_context": r.input_context,
                "generated_content": r.generated_content,
                "is_high_quality_example": r.is_high_quality_example,
                "tags": r.tags,
            }
            if r.user_edits:
                obj["user_edits"] = {
                    "original_text": r.user_edits.original_text,
                    "edited_text": r.user_edits.edited_text,
                    "change_ratio": r.user_edits.change_ratio,
                }
            if r.user_feedback:
                obj["user_feedback"] = {
                    "rating": r.user_feedback.rating,
                    "is_positive": r.user_feedback.is_positive,
                    "review_comments": r.user_feedback.review_comments,
                }
            lines.append(json.dumps(obj, ensure_ascii=False))
        return "\n".join(lines)


learning_dataset_service = LearningDatasetService(storage_path=DEFAULT_STORAGE_FILE)
