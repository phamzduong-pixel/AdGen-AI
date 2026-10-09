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
│   └── requirements*.txt       # Backend Python dependencies
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
│   │   │       └── TrendReportPanel/
│   │   ├── constants/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/               # Application pages, including Chat
│   │   ├── routes/
│   │   ├── services/api/
│   │   │   └── trendReportApi.js
│   │   ├── styles/
│   │   ├── types/
│   │   └── utils/
│   │       └── trendReportSourceStatus.js
│   ├── tests/
│   │   └── trendReportSourceStatus.test.js
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

Current synchronization notes (07/10/2026):

- Alembic head is `20261006_0025_trend_report_history_soft_delete`.
- Trend Radar Stage 3/4 boundaries also include `backend/app/api/insight_campaign.py`, `backend/app/services/trend_monitor_service.py`, `trend_alert_service.py`, `advertising_angle_service.py` and `insight_campaign_service.py`.
- Frontend Trend Radar rendering is in `frontend/src/components/chat/TrendReportPanel/`; its API client and normalization utilities are under `frontend/src/services/api/trendReportApi.js` and `frontend/src/utils/trendReport*.js`.
- Voice Studio boundaries gồm `backend/app/services/voiceover/`, `backend/app/services/stt/`, `backend/app/services/voice_conversion/`, các router `voiceover.py`/`stt.py`/`video_stt.py`/`voice_conversion.py`, và `frontend/src/components/chat/VoiceoverModal/`.
- Seed-VC reference assets nằm tại `backend/app/assets/ref_audios/`; runtime/checkpoint được giữ ngoài repository và cấu hình bằng `SEED_VC_PYTHON`, `SEED_VC_DIR`.
