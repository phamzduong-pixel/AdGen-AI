# AdGenAI Project Tree

This document is a navigational snapshot of the repository structure. It focuses on source code, tests, migrations, and documentation; generated files, virtual environments, caches, uploads, and dependency directories are intentionally omitted.

```text
AdGenAI/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 20261003_0017_voiceover_audio_ownership.py
│   ├── app/
│   │   ├── api/                 # FastAPI routers and authenticated endpoints
│   │   ├── core/                # Configuration, security, and shared backend concerns
│   │   ├── data/                # Local application data and datasets
│   │   ├── database/            # Session setup and schema metadata/state
│   │   ├── models/              # SQLAlchemy models: core, media, voiceover
│   │   ├── prompts/             # Prompt templates and prompt resources
│   │   ├── schemas/             # Pydantic request/response contracts
│   │   └── services/
│   │       ├── external_retrieval/
│   │       │   ├── evidence_context.py
│   │       │   └── multi_platform.py
│   │       ├── product_trust/
│   │       ├── ai_service.py
│   │       ├── message_service.py
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
│   │   │       └── VoiceoverModal/         # text/file source, STT, TTS, reference voice
│   │   ├── constants/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/               # Application pages, including Chat
│   │   ├── routes/
│   │   ├── services/api/                   # client API theo domain
│   │   │   ├── chatApi.js
│   │   │   └── voiceoverApi.js
│   │   ├── styles/
│   │   ├── types/
│   │   └── utils/                         # Domain helpers
│   ├── tests/
│   │   └── voiceover*.test.js
│   └── package.json
├── .agents/                     # Local agent/project support files
├── docker-compose.yml           # Local service orchestration, when present
├── render.yaml                  # Deployment configuration, when present
└── README.md                    # Repository quick-start guide, when present
```

## Maintenance note

This is a curated navigation tree rather than an exhaustive generated file listing. Update it when a top-level application boundary, migration head, or test location changes.

Current synchronization notes (14/10/2026):

- Alembic head is revision `20261006_0025`.
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
- frontend/tests/: contract/unit tests cho UI utilities, content workflow và Voice Studio.
- backend/checkpoints/, virtual environments, model caches, uploads và generated audio không được xem là source tree; chúng cần được quản lý riêng, không tự động xóa khi dọn source.

## Update rule

Khi thêm endpoint, service boundary, provider, migration head, file reference hoặc nhóm test mới, cập nhật đồng thời docs/00-tong-quan-he-thong.md, docs/02-luong-xu-ly-ai.md, docs/03-co-so-du-lieu.md, docs/10-adgen-ai-capstone-final-report.md và tài liệu này.
