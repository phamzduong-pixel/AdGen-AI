import unittest
from datetime import datetime
from datetime import timedelta

from app.core.datetime_utils import utc_now

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.campaign import CampaignContent
from app.models.content_activity import ContentActivity
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.uploaded_file import UploadedFile  # noqa: F401
from app.models.user import User
from app.schemas.campaign import CampaignCreate
from app.services.campaign_service import add_campaign_content_service
from app.services.campaign_service import create_campaign_service
from app.services.campaign_service import delete_campaign_service
from app.services.campaign_service import get_campaign_detail_service
from app.services.campaign_service import set_primary_content_service
from app.services.dashboard_service import get_dashboard_activity_service
from app.services.dashboard_service import get_dashboard_summary_service
from app.services.dashboard_service import get_platform_usage_service


class CampaignDashboardTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.owner = User(
            username="campaign-owner",
            email="campaign@example.com",
            hashed_password="test",
        )
        self.other = User(
            username="campaign-other",
            email="other-campaign@example.com",
            hashed_password="test",
        )
        self.db.add_all([self.owner, self.other])
        self.db.flush()
        self.conversation = Conversation(title="Owner", user_id=self.owner.id)
        other_conversation = Conversation(title="Other", user_id=self.other.id)
        self.db.add_all([self.conversation, other_conversation])
        self.db.flush()
        now = utc_now()
        self.db.add_all(
            [
                Message(
                    conversation_id=self.conversation.id,
                    role="user",
                    content="Prompt",
                    prompt_type="facebook",
                    created_at=now - timedelta(days=1),
                ),
                Message(
                    conversation_id=self.conversation.id,
                    role="assistant",
                    content="Generated",
                    created_at=now - timedelta(days=1),
                ),
                Message(
                    conversation_id=other_conversation.id,
                    role="assistant",
                    content="Private generated",
                    created_at=now,
                ),
            ]
        )
        self.db.flush()
        self.saved_one = SavedContent(
            user_id=self.owner.id,
            conversation_id=self.conversation.id,
            message_id=None,
            title="Content A",
            content="A",
            platform="facebook",
        )
        self.saved_two = SavedContent(
            user_id=self.owner.id,
            conversation_id=self.conversation.id,
            message_id=None,
            title="Content B",
            content="B",
            platform="facebook",
        )
        other_saved = SavedContent(
            user_id=self.other.id,
            conversation_id=other_conversation.id,
            message_id=None,
            title="Private",
            content="Private",
            platform="tiktok",
        )
        self.db.add_all([self.saved_one, self.saved_two, other_saved])
        self.db.flush()
        self.other_saved_id = other_saved.id
        self.db.add_all(
            [
                ContentActivity(
                    user_id=self.owner.id,
                    saved_content_id=self.saved_one.id,
                    action_type="evaluation",
                    score=86,
                    platform="facebook",
                    quantity=1,
                ),
                ContentActivity(
                    user_id=self.owner.id,
                    saved_content_id=self.saved_one.id,
                    action_type="variants_generated",
                    platform="facebook",
                    quantity=3,
                ),
                ContentActivity(
                    user_id=self.other.id,
                    action_type="evaluation",
                    score=99,
                    platform="tiktok",
                    quantity=1,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_campaign_links_are_owned_unique_and_primary_is_exclusive(self):
        campaign = create_campaign_service(
            CampaignCreate(name="Summer", platform="facebook"),
            self.db,
            self.owner,
        )
        add_campaign_content_service(
            campaign.id,
            self.saved_one.id,
            self.db,
            self.owner,
        )
        duplicate = add_campaign_content_service(
            campaign.id,
            self.saved_one.id,
            self.db,
            self.owner,
        )
        self.assertEqual(duplicate.contents_count, 1)

        with self.assertRaises(HTTPException) as context:
            add_campaign_content_service(
                campaign.id,
                self.other_saved_id,
                self.db,
                self.owner,
            )
        self.assertEqual(context.exception.status_code, 404)

        add_campaign_content_service(
            campaign.id,
            self.saved_two.id,
            self.db,
            self.owner,
        )
        set_primary_content_service(
            campaign.id,
            self.saved_one.id,
            self.db,
            self.owner,
        )
        detail = set_primary_content_service(
            campaign.id,
            self.saved_two.id,
            self.db,
            self.owner,
        )
        primaries = [
            item.saved_content.id for item in detail.contents if item.is_primary
        ]
        self.assertEqual(primaries, [self.saved_two.id])

        saved_id = self.saved_one.id
        delete_campaign_service(campaign.id, self.db, self.owner)
        self.assertIsNotNone(self.db.get(SavedContent, saved_id))
        self.assertEqual(
            self.db.query(CampaignContent)
            .filter(CampaignContent.campaign_id == campaign.id)
            .count(),
            0,
        )

    def test_dashboard_aggregates_only_current_user(self):
        summary = get_dashboard_summary_service(self.db, self.owner)
        self.assertEqual(summary.total_conversations, 1)
        self.assertEqual(summary.total_generated_contents, 1)
        self.assertEqual(summary.total_saved_contents, 2)
        self.assertEqual(summary.total_evaluations, 1)
        self.assertEqual(summary.total_variants, 3)
        self.assertEqual(summary.top_platform, "facebook")
        self.assertEqual(summary.contents_last_7_days, 1)

        activity = get_dashboard_activity_service(self.db, self.owner)
        self.assertEqual(len(activity.days), 30)
        self.assertEqual(sum(day.count for day in activity.days), 1)

        platforms = get_platform_usage_service(self.db, self.owner)
        self.assertEqual(len(platforms.platforms), 1)
        self.assertEqual(platforms.platforms[0].platform, "facebook")
        self.assertEqual(platforms.platforms[0].average_score, 86)

    def test_non_owner_cannot_read_campaign(self):
        campaign = create_campaign_service(
            CampaignCreate(name="Private campaign"),
            self.db,
            self.owner,
        )
        with self.assertRaises(HTTPException) as context:
            get_campaign_detail_service(campaign.id, self.db, self.other)
        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
