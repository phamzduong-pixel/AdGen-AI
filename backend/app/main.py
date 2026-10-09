from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.conversation import router as conversation_router
from app.api.content import router as content_router
from app.api.campaign import router as campaign_router
from app.api.dashboard import router as dashboard_router
from app.api.message import router as message_router
from app.api.saved_content import router as saved_content_router
from app.api.upload import router as upload_router
from app.api.user import router as user_router
from app.api.template import router as template_router
from app.api.brand import router as brand_router
from app.api.content_document import router as content_document_router
from app.api.voiceover import router as voiceover_router
from app.api.stt import router as stt_router
from app.api.video_stt import router as video_stt_router
from app.api.voice_conversion import router as voice_conversion_router
from app.api.media import router as media_router
from app.api.trend_report import router as trend_report_router
from app.api.insight_campaign import router as insight_campaign_router
from app.database.database import initialize_database
from app.database.database import SessionLocal
from app.core.config import settings
from app.services.template_service import seed_system_templates


app = FastAPI(
    title="AdGen AI API",
    version="1.0.0",
    debug=not settings.is_production,
)


@app.on_event("startup")
def startup_database():
    settings.validate()
    initialize_database()
    with SessionLocal() as db:
        seed_system_templates(db)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(conversation_router)
app.include_router(content_router)
app.include_router(campaign_router)
app.include_router(dashboard_router)
app.include_router(message_router)
app.include_router(saved_content_router)
app.include_router(upload_router)
app.include_router(user_router)
app.include_router(template_router)
app.include_router(brand_router)
app.include_router(content_document_router)
app.include_router(voiceover_router)
app.include_router(stt_router)
app.include_router(video_stt_router)
app.include_router(voice_conversion_router)
app.include_router(media_router)
app.include_router(trend_report_router)
app.include_router(insight_campaign_router)


@app.get("/")
def root():
    return {
        "message": "AdGen AI Backend Running",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "adgen-ai-api"}
