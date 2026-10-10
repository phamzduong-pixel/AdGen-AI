"""Shared unittest boundary for isolating AI learning-dataset writes."""

from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app.services import ai_service
from app.services.learning_dataset.service import DEFAULT_STORAGE_FILE, LearningDatasetService


@contextmanager
def isolated_ai_writer(*, persist_to_temp: bool = False):
    """Isolate ``ai_service._log_generation`` from the real dataset."""
    if persist_to_temp:
        with TemporaryDirectory(prefix="adgen-ai-learning-test-") as directory:
            target = Path(directory) / "learning_dataset.jsonl"
            isolated_service = LearningDatasetService(storage_path=target)
            with patch.object(ai_service, "learning_dataset_service", isolated_service):
                yield isolated_service, target
        return

    blocked_writer = Mock(name="blocked_learning_dataset_writer")
    with patch.object(
        ai_service.learning_dataset_service,
        "log_generation",
        blocked_writer,
    ):
        yield blocked_writer, None


def block_ai_writer(test_method):
    @wraps(test_method)
    def wrapped(test_case):
        with isolated_ai_writer() as (blocked_writer, _):
            result = test_method(test_case)
        blocked_writer.assert_called_once()
        return result

    return wrapped


@contextmanager
def temporary_learning_dataset_service():
    with TemporaryDirectory() as directory:
        target = Path(directory) / DEFAULT_STORAGE_FILE.name
        yield LearningDatasetService(storage_path=target), target
