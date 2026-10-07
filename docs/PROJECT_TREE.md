# AdGenAI Project Tree

This document is a navigational snapshot of the repository structure. It focuses on source code, tests, migrations, and documentation; generated files, virtual environments, caches, uploads, and dependency directories are intentionally omitted.

```text
AdGenAI/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 20261005_0018_trend_report_evidence_store.py
│   │       └── 20261005_0019_trend_report_source_statuses.py
│   ├── app/
│   │   ├── api/                 # FastAPI routers and authenticated endpoints
│   │   ├── core/                # Configuration, security, and shared backend concerns
│   │   ├── data/                # Local application data and datasets
│   │   ├── database/            # Session setup and schema metadata/state
│   │   ├── models/              # SQLAlchemy models
│   │   ├── prompts/             # Prompt templates and prompt resources
│   │   ├── schemas/             # Pydantic request/response contracts
│   │   └── services/
│   │       ├── external_retrieval/
│   │       │   ├── evidence_context.py
│   │       │   └── multi_platform.py
│   │       ├── product_trust/
│   │       ├── ai_service.py
│   │       ├── message_service.py
│   │       └── trend_report_service.py
│   ├── smoke/                   # Backend smoke checks
│   ├── tests/                   # Backend unit, integration, and checkpoint tests
│   │   ├── test_multi_platform_retrieval.py
│   │   ├── test_source_status_round_trip.py
│   │   ├── test_trend_report.py
│   │   └── test_trend_report_stage2_api.py
│   └── requirements*.txt       # Backend Python dependencies
├── docs/
│   ├── README.md                # Documentation index and source-of-truth pointers
│   ├── PROJECT_TREE.md          # This file
│   ├── 17-plan-adgen-trend-radar.md
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
- Plan and implementation status: `docs/17-plan-adgen-trend-radar.md`

## Maintenance note

This is a curated navigation tree rather than an exhaustive generated file listing. Update it when a top-level application boundary, Plan 17 integration point, migration head, or test location changes.
