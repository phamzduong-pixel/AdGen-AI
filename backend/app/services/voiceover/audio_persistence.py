"""Persistence helpers for generated Voice Studio audio files."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.models.voiceover_audio import VoiceoverAudio


class VoiceoverMessageLinkError(ValueError):
    """Raised when an optional voiceover message link is invalid or not owned."""

    status_code = 404
    detail = "Tin nhắn không tồn tại hoặc không thuộc tài khoản."


def resolve_owned_message_id(
    raw_message_id: str | int | None,
    *,
    db: Session,
    current_user: User,
) -> int | None:
    """Validate and normalize the optional message association."""

    if raw_message_id is None or str(raw_message_id).strip() == "":
        return None

    try:
        message_id = int(raw_message_id)
    except (TypeError, ValueError) as error:
        invalid = VoiceoverMessageLinkError("message_id không hợp lệ.")
        invalid.status_code = 400
        invalid.detail = "message_id không hợp lệ."
        raise invalid from error

    linked_message = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Message.id == message_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if linked_message is None:
        raise VoiceoverMessageLinkError
    return message_id


def persist_latest_voiceover(
    *,
    db: Session,
    audio_dir: Path,
    user_id: int,
    message_id: int | None,
    audio_id: str,
    filename: str,
    file_size_bytes: int,
    duration_seconds: float | None,
    voice_id: str,
) -> VoiceoverAudio:
    """Persist one audio and replace the previous audio for the same message."""

    previous_records = []
    if message_id is not None:
        previous_records = (
            db.query(VoiceoverAudio)
            .filter(
                VoiceoverAudio.user_id == user_id,
                VoiceoverAudio.message_id == message_id,
            )
            .all()
        )
        for previous in previous_records:
            db.delete(previous)

    record = VoiceoverAudio(
        audio_id=audio_id,
        filename=filename,
        user_id=user_id,
        message_id=message_id,
        file_size_bytes=file_size_bytes,
        duration_seconds=duration_seconds or 0.0,
        voice_id=voice_id,
    )
    db.add(record)
    db.commit()

    for previous in previous_records:
        try:
            (audio_dir / previous.filename).unlink(missing_ok=True)
        except OSError:
            # Database ownership is already correct; an orphan cleanup job can
            # remove an inaccessible old file later without hiding the result.
            pass

    return record


def persist_latest_voiceover_record(
    *,
    db: Session,
    audio_dir: Path,
    record: VoiceoverAudio,
) -> VoiceoverAudio:
    previous_records = []
    if record.message_id is not None:
        previous_records = (
            db.query(VoiceoverAudio)
            .filter(
                VoiceoverAudio.user_id == record.user_id,
                VoiceoverAudio.message_id == record.message_id,
            )
            .all()
        )
        for previous in previous_records:
            db.delete(previous)

    db.add(record)
    db.commit()
    for previous in previous_records:
        try:
            (audio_dir / previous.filename).unlink(missing_ok=True)
        except OSError:
            pass
    return record
