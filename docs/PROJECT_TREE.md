# AdGenAI Project Tree

This document is a navigational snapshot of the repository structure. It focuses on source code, tests, migrations, and documentation; generated files, virtual environments, caches, uploads, and dependency directories are intentionally omitted.

```text
AdGenAI/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 20261003_0017_voiceover_audio_ownership.py
│   │       ├── 20261005_0018_trend_report_evidence_store.py
│   │       ├── 20261005_0019_trend_report_source_statuses.py
│   │       ├── 20261006_0020_product_trust_policies.py
│   │       ├── 20261006_0021_trend_monitor_foundation.py
│   │       ├── 20261006_0022_trend_alert_engine.py
│   │       ├── 20261006_0023_advertising_angles.py
│   │       ├── 20261006_0024_insight_campaign_metrics.py
│   │       └── 20261006_0025_trend_report_history_soft_delete.py
│   ├── app/
│   │   ├── api/                 # FastAPI routers and authenticated endpoints
│   │   ├── core/                # Configuration, security, and shared backend concerns
│   │   ├── data/                # Local application data and datasets
│   │   ├── database/            # Session setup and schema metadata/state
│   │   ├── models/              # SQLAlchemy models: core, media, voiceover, Trend Radar
│   │   ├── prompts/             # Prompt templates and prompt resources
│   │   ├── schemas/             # Pydantic request/response contracts
│   │   └── services/
│   │       ├── external_retrieval/
│   │       │   ├── evidence_context.py
│   │       │   └── multi_platform.py
│   │       ├── product_trust/
│   │       ├── ai_service.py
│   │       ├── message_service.py
│   │       ├── trend_report_service.py
│   │       ├── trend_monitor_service.py
│   │       ├── trend_alert_service.py
│   │       ├── advertising_angle_service.py
│   │       ├── insight_campaign_service.py
│   │       └── voiceover/
│   │           ├── audio_persistence.py       # lưu ownership và thay audio mới nhất theo message
│   │           ├── emotion.py                 # chuẩn hóa cue biểu cảm cho VieNeu
│   │           ├── extractor.py               # lọc phần lời thoại từ script
│   │           ├── script_cleaner.py           # làm sạch nội dung trước TTS
│   │           ├── voiceover_service.py        # orchestration TTS/reference voice
│   │           └── providers/                  # Edge TTS, mock và VieNeu worker/provider
│   ├── smoke/                   # Backend smoke checks
│   ├── tests/                   # Backend unit, integration, and checkpoint tests
│   │   ├── test_multi_platform_retrieval.py
│   │   ├── test_source_status_round_trip.py
│   │   ├── test_trend_report.py
│   │   ├── test_trend_report_stage2_api.py
│   │   ├── test_product_trust_report.py
│   │   ├── test_trend_monitor_foundation.py
│   │   ├── test_trend_alert_lifecycle.py
│   │   ├── test_trend_alert_integration.py
│   │   ├── test_insight_campaign_service.py
│   │   └── test_voiceover_extractor.py
│   └── requirements*.txt       # runtime và development dependencies (gồm requirements-dev.txt)
├── docs/
│   ├── README.md                # Documentation index and source-of-truth pointers
│   ├── PROJECT_TREE.md          # This file
│   └── other system and operations documentation
├── frontend/
│   ├── public/                  # Static public assets
│   ├── src/
│   │   ├── assets/
│   │   ├── components/          # Reusable UI components
│   │   │   └── chat/
│   │   │       ├── ChatInput/              # nhận text, brief, platform, brand và file
│   │   │       ├── TrendReportPanel/       # Trend Radar UI
│   │   │       └── VoiceoverModal/         # text/file source, STT, TTS, reference voice
│   │   ├── constants/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/               # Application pages, including Chat
│   │   ├── routes/
│   │   ├── services/api/                   # client API theo domain
│   │   │   ├── chatApi.js
│   │   │   ├── voiceoverApi.js
│   │   │   └── trendReportApi.js
│   │   ├── styles/
│   │   ├── types/
│   │   └── utils/
│   │       └── trendReportSourceStatus.js
│   ├── tests/
│   │   ├── trendReportSourceStatus.test.js
│   │   └── voiceover*.test.js
│   └── package.json
├── .agents/                     # Local agent/project support files
├── docker-compose.yml           # Local service orchestration, when present
├── render.yaml                  # Deployment configuration, when present
└── README.md                    # Repository quick-start guide, when present
```

## Plan 17 locations

The main Trend Radar implementation is distributed across these boundaries:

- Backend API: `backend/app/api/trend_report.py`
- Retrieval orchestration: `backend/app/services/external_retrieval/multi_platform.py`
- Evidence context and provenance: `backend/app/services/external_retrieval/evidence_context.py`
- Trend Report persistence: `backend/app/models/trend_report.py` and `backend/app/services/trend_report_service.py`
- Request/response contracts: `backend/app/schemas/trend_report.py`
- Database changes: `backend/alembic/versions/20261005_0018_trend_report_evidence_store.py` and `20261005_0019_trend_report_source_statuses.py`
- UI API client: `frontend/src/services/api/trendReportApi.js`
- UI comparison panel: `frontend/src/components/chat/TrendReportPanel/`
- UI status normalization/rendering: `frontend/src/utils/trendReportSourceStatus.js`
- Voice Studio plan and implementation status: `docs/01-chuc-nang-he-thong.md`

## Maintenance note

This is a curated navigation tree rather than an exhaustive generated file listing. Update it when a top-level application boundary, Plan 17 integration point, migration head, or test location changes.

Current synchronization notes (12/10/2026):

- Alembic head is `20261006_0025_trend_report_history_soft_delete`.
- Trend Radar Stage 3/4 boundaries also include `backend/app/api/insight_campaign.py`, `backend/app/services/trend_monitor_service.py`, `trend_alert_service.py`, `advertising_angle_service.py` and `insight_campaign_service.py`.
- Frontend Trend Radar rendering is in `frontend/src/components/chat/TrendReportPanel/`; its API client and normalization utilities are under `frontend/src/services/api/trendReportApi.js` and `frontend/src/utils/trendReport*.js`.
- Voice Studio boundaries gồm `backend/app/services/voiceover/`, `backend/app/services/stt/`, `backend/app/services/voice_conversion/`, các router `voiceover.py`/`stt.py`/`video_stt.py`/`voice_conversion.py`, và `frontend/src/components/chat/VoiceoverModal/`.
- Seed-VC reference assets nằm tại `backend/app/assets/ref_audios/`; runtime/checkpoint được giữ ngoài repository và cấu hình bằng `SEED_VC_PYTHON`, `SEED_VC_DIR`.

## Current application boundaries and file roles

### Conversation input and AI pipeline

- frontend/src/pages/Chat/Chat.jsx: màn hình hội thoại và điều phối trạng thái conversation.
- frontend/src/components/chat/ChatInput/: nhận input người dùng, brief, platform, brand và attachment.
- frontend/src/services/api/chatApi.js: gọi non-stream/stream message API.
- backend/app/api/message.py: HTTP boundary, JWT, ownership và request contract.
- backend/app/services/message_service.py: commit user message, retrieval gate, stream lifecycle và lưu canonical assistant.
- backend/app/services/context_engine/: follow-up intent, context model và history pruning.
- backend/app/services/external_retrieval/: retrieval đa nền tảng, evidence normalization và provenance.
- backend/app/services/prompt_service.py: ghép system rules, platform, brand/product context và request.
- backend/app/services/ai_service.py: gọi text provider và trả stream/non-stream.
- backend/app/services/output_validator/ và product_trust/: kiểm tra output, claim, evidence và trust gate.

### Voice Studio pipeline

- frontend/src/components/chat/VoiceoverModal/: UI text/file source, transcript review, chọn giọng, tốc độ, emotion, reference file và audio result.
- frontend/src/services/api/voiceoverApi.js: client của clean, STT, TTS, reference voice và direct conversion.
- backend/app/api/voiceover.py: endpoint clean/generate/audio và persistence ownership.
- backend/app/api/stt.py, video_stt.py: nhận dạng audio/video.
- backend/app/api/voice_conversion.py: endpoint chuyển giọng trực tiếp.
- backend/app/services/voiceover/: script cleaner, emotion cue, Edge TTS, VieNeu-TTS, output validation và persistence.
- backend/app/services/stt/: provider factory, Vosk, Google adapter và fail-closed provider.
- backend/app/services/voice_studio/: probe video và extraction audio.
- backend/app/services/voice_conversion/: audio probe, reference manager, Seed-VC converter và provider factory.
- backend/app/assets/ref_audios/ngoc_huyen_ref.wav: reference/preset asset hiện có trong repository.

### Frontend navigation and cleanup result

- frontend/src/components/navigation/AppNavigation/navigationItems.js: danh sách menu dùng chung, tách khỏi component để tránh lỗi Fast Refresh/ESLint.
- frontend/src/components/navigation/AppNavigation/AppNavigation.jsx: render menu điều hướng.
- Các placeholder UI rỗng, API legacy không còn import và thư mục Sidebar/ConversationItem/ trùng đã được loại bỏ sau khi kiểm tra dependency.

### Tests and runtime boundaries

- backend/tests/: test unit/API/integration cho auth, database, chat lifecycle, retrieval, media, STT, voiceover, emotion và voice conversion.
- frontend/tests/: contract/unit tests cho UI utilities, content workflow, Trend Radar và Voice Studio.
- backend/checkpoints/, virtual environments, model caches, uploads và generated audio không được xem là source tree; chúng cần được quản lý riêng, không tự động xóa khi dọn source.

## Update rule

Khi thêm endpoint, service boundary, provider, migration head, file reference hoặc nhóm test mới, cập nhật đồng thời docs/00-tong-quan-he-thong.md, docs/02-luong-xu-ly-ai.md, docs/03-co-so-du-lieu.md, docs/10-adgen-ai-capstone-final-report.md và tài liệu này.
