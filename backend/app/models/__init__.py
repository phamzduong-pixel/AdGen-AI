"""Import every model so SQLAlchemy metadata is complete for Alembic."""

from app.models.campaign import Campaign, CampaignContent
from app.models.brand import BrandAsset, BrandContentCheck, BrandProfile
from app.models.ad_template import AdTemplate, TemplateFavorite
from app.models.content_activity import ContentActivity
from app.models.content_document import ContentDocument, ContentVersion
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.password_reset import PasswordResetToken
from app.models.email_verification import EmailVerificationToken
from app.models.saved_content import SavedContent
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.user_session import UserSession
from app.models.media_asset import MediaAsset
from app.models.media_job import MediaJob
from app.models.media_request import MediaEditRequest
from app.models.voiceover_audio import VoiceoverAudio
from app.models.evidence_source_policy import EvidenceSourcePolicy
from app.models.trend_monitor import TrendMonitor, TrendSnapshot
from app.models.trend_alert import TrendAlert
from app.models.advertising_angle import AdvertisingAngle
from app.models.advertising_brief import AdvertisingBrief, CampaignMetricSnapshot
from app.models.trend_report import (
    TrendReport,
    TrendReportClaim,
    TrendReportClaimEvidence,
    TrendReportEvidence,
)

__all__ = [
    'EvidenceSourcePolicy',
    'TrendMonitor',
    'TrendSnapshot',
    'TrendAlert',
    'AdvertisingAngle',
    'AdvertisingBrief',
    'CampaignMetricSnapshot',
    "Campaign",
    "BrandProfile",
    "BrandAsset",
    "BrandContentCheck",
    "CampaignContent",
    "AdTemplate",
    "TemplateFavorite",
    "ContentActivity",
    "ContentDocument",
    "ContentVersion",
    "Conversation",
    "Message",
    "PasswordResetToken",
    "EmailVerificationToken",
    "SavedContent",
    "UploadedFile",
    "User",
    "UserSettings",
    "UserSession",
    "MediaAsset",
    "MediaJob",
    "MediaEditRequest",
    "VoiceoverAudio",
    "TrendReport",
    "TrendReportClaim",
    "TrendReportClaimEvidence",
    "TrendReportEvidence",
]
