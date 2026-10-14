# Cây thư mục và vai trò file — AdGen AI

Tài liệu này là cây điều hướng các file đầu mối của hệ thống, không thay cho danh sách mọi file trong repository. Mỗi file được nêu đều có vai trò bên cạnh. Các thư mục con chứa thêm component, style và test cùng miền chức năng.

```text
AdGenAI/
├── .env.example                         # Mẫu biến môi trường gốc; không phải cấu hình runtime
├── README.md                            # Giới thiệu repo và hướng dẫn bắt đầu
├── docker-compose.yml                   # Chạy các dịch vụ local, gồm PostgreSQL và backend/frontend
├── render.yaml                          # Cấu hình triển khai AdGen AI trên Render
├── backend/
│   ├── Dockerfile                       # Đóng gói backend
│   ├── requirements.txt                 # Dependency runtime Python
│   ├── requirements-dev.txt             # Dependency phục vụ phát triển/kiểm thử
│   ├── .env.example                     # Mẫu cấu hình backend; DATABASE_URL là cấu hình mẫu
│   ├── adgen.db, adgen_dev.db, chatbot.db # SQLite local đang có; DATABASE_URL mới quyết định file nào được chọn
│   ├── alembic.ini                      # Cấu hình công cụ migration Alembic
│   ├── alembic/
│   │   ├── env.py                       # Kết nối Alembic với Base.metadata và database URL
│   │   ├── script.py.mako               # Mẫu tạo file migration
│   │   └── versions/                   # 25 migration từ 0001 đến 0025; chi tiết ở bảng bên dưới
│   ├── app/
│   │   ├── main.py                      # Khởi tạo FastAPI, router, CORS và kiểm tra DB lúc startup
│   │   ├── assets/
│   │   │   └── ref_audios/ngoc_huyen_ref.wav # Audio mẫu/reference có trong repo cho Voice Studio
│   │   ├── api/                         # HTTP endpoints, validation và dependency auth
│   │   ├── core/                        # Cấu hình, bảo mật, thời gian và nền tảng quảng cáo
│   │   ├── data/                        # Dataset cục bộ; learning_dataset.jsonl dùng bởi luồng learning dataset
│   │   ├── database/                    # Engine/session, manifest, schema validation và bootstrap
│   │   ├── models/                      # SQLAlchemy models cho 34 bảng ứng dụng
│   │   ├── prompts/                     # System prompt và prompt theo loại nội dung/nền tảng
│   │   ├── schemas/                     # Hợp đồng request/response Pydantic theo miền
│   │   └── services/                    # Nghiệp vụ, provider và tích hợp của backend
│   ├── smoke/                           # Script smoke test cục bộ; không phải endpoint sản phẩm
│   ├── tests/                           # Test backend unit/API/integration, dùng mock/fixture theo từng test
│   └── checkpoints/                     # Cache/trọng số model có mặt cục bộ; không phải mã nguồn ứng dụng
├── docs/
│   ├── README.md                        # Mục lục tài liệu
│   ├── PROJECT_TREE.md                  # Cây thư mục này và vai trò file đầu mối
│   └── 00–10-*.md                       # Tổng quan, kiến trúc, CSDL, API, vận hành và báo cáo
├── frontend/
│   ├── Dockerfile                       # Đóng gói frontend
│   ├── package.json                     # Script và dependency frontend
│   ├── package-lock.json                # Khóa phiên bản dependency npm
│   ├── vite.config.js                   # Cấu hình Vite
│   ├── nginx.conf                       # Cấu hình phục vụ SPA qua Nginx
│   ├── index.html                       # HTML entry point
│   ├── eslint.config.js                 # Quy tắc lint
│   ├── .env.example                     # Mẫu biến môi trường frontend
│   ├── public/                          # Tài nguyên tĩnh được phục vụ nguyên trạng
│   │   ├── _redirects                   # Fallback URL về SPA khi deploy
│   │   ├── favicon.svg                  # Icon tab trình duyệt
│   │   └── icons.svg                    # Sprite icon dùng công khai
│   ├── src/
│   │   ├── main.jsx                      # React bootstrap và context providers
│   │   ├── App.jsx                       # Root app component
│   │   ├── routes/                       # Định nghĩa route và protected route
│   │   ├── layouts/                      # Khung Workspace và Chat
│   │   ├── pages/                        # Trang Chat, Dashboard, Campaigns, Brands, Library, Settings, Auth…
│   │   ├── components/                   # Component giao diện theo miền
│   │   ├── context/                      # AuthContext và ThemeContext
│   │   ├── hooks/                        # State và hành vi tái sử dụng theo miền
│   │   ├── services/api/                 # Axios client và API client theo chức năng
│   │   ├── services/storage/             # Lưu token phía client
│   │   ├── constants/                    # Hằng số API và nền tảng
│   │   ├── styles/                       # Biến, reset, markdown, scrollbar và animation
│   │   ├── utils/                        # Xử lý nội dung, trạng thái và chuyển đổi dữ liệu
│   │   └── assets/                       # Asset được import trong mã frontend
│   └── tests/                            # Test frontend Node test runner, contract và utility
└── .agents/                              # Tài liệu/quy tắc hỗ trợ agent trong repo
```

## Vai trò các file đầu mối

### Backend: API, cấu hình, database và schema

| File | Vai trò |
| --- | --- |
| `backend/app/api/auth.py` | Đăng nhập, đăng ký và token |
| `backend/app/api/user.py` | Hồ sơ và cài đặt người dùng |
| `backend/app/api/conversation.py` | Tạo, liệt kê, ghim, đổi tên và xóa hội thoại |
| `backend/app/api/message.py` | Gửi tin nhắn chat thường và streaming |
| `backend/app/api/upload.py` | Upload và truy cập tệp đính kèm |
| `backend/app/api/brand.py` | API hồ sơ và tài sản thương hiệu |
| `backend/app/api/campaign.py` | API chiến dịch và nội dung chiến dịch |
| `backend/app/api/content.py` | Công cụ, biến thể và thao tác nội dung |
| `backend/app/api/content_document.py` | Tài liệu nội dung và lịch sử phiên bản |
| `backend/app/api/dashboard.py` | Thống kê dashboard |
| `backend/app/api/insight_campaign.py` | Góc quảng cáo, brief và snapshot chỉ số |
| `backend/app/api/media.py` | Asset/job và endpoint Media Studio; tạo mới đang bị khóa khi trạng thái đang phát triển |
| `backend/app/api/saved_content.py` | Lưu và truy xuất nội dung đã lưu |
| `backend/app/api/template.py` | Mẫu quảng cáo và yêu thích mẫu |
| `backend/app/api/voiceover.py` | Tạo, lấy và quản lý audio voiceover |
| `backend/app/api/stt.py`, `video_stt.py` | Nhận dạng lời nói từ audio/video |
| `backend/app/api/voice_conversion.py` | Chuyển giọng trực tiếp từ tệp nguồn |
| `backend/app/api/trend_report.py` | API RSS/Trend Report còn được giữ; giao diện truy cập đã tạm ẩn |

| File | Vai trò |
| --- | --- |
| `backend/app/core/config.py` | Đọc cấu hình môi trường và chuẩn hóa database/provider settings |
| `backend/app/core/security.py` | Hash mật khẩu, JWT và tiện ích bảo mật |
| `backend/app/core/datetime_utils.py` | Chuẩn hóa thời gian UTC |
| `backend/app/core/platforms.py` | Hằng số và quy tắc nền tảng quảng cáo |
| `backend/app/database/database.py` | Engine, `SessionLocal`, `Base`, `get_db()` và startup schema guard |
| `backend/app/database/schema_manifest.py` | Định nghĩa schema ứng dụng chuẩn |
| `backend/app/database/schema_validator.py` | So sánh cấu trúc database với manifest/model |
| `backend/app/database/schema_state.py` | Đọc trạng thái schema và revision Alembic |
| `backend/app/database/bootstrap.py` | Bootstrap có xác nhận cho database thực sự rỗng |
| `backend/app/database/prepare_database.py` | Chuẩn bị database và xác nhận trạng thái trước khi chạy |
| `backend/app/database/legacy_reconciliation.py` | Báo cáo tình trạng database legacy; không tự sửa |
| `backend/app/models/__init__.py` | Import model để đăng ký metadata với SQLAlchemy |
| `backend/app/schemas/` | Các file Pydantic trong thư mục định nghĩa request/response; xem từng domain cùng tên API/model |
| `backend/app/data/learning_dataset.jsonl` | Dataset cục bộ cho luồng learning dataset; không phải database quan hệ |
| `backend/app/assets/ref_audios/ngoc_huyen_ref.wav` | Audio tham chiếu mẫu có trong repo cho Voice Studio |

Các model CSDL và 34 bảng được liệt kê chi tiết tại [03-co-so-du-lieu.md](03-co-so-du-lieu.md). `backend/app/models/*.py` định nghĩa cấu trúc bảng; file migration chỉ mô tả thay đổi schema qua từng phiên bản. Không nhầm các file `.db` runtime với phần định nghĩa schema.

### Backend: service và provider

| File hoặc nhóm file | Vai trò |
| --- | --- |
| `backend/app/services/message_service.py` | Điều phối vòng đời chat, lưu message và nối retrieval/AI |
| `backend/app/services/ai_service.py` | Gọi text model/provider và trả kết quả thường hoặc streaming |
| `backend/app/services/prompt_service.py`, `brand_prompt.py` | Ghép prompt hệ thống, nền tảng và ngữ cảnh thương hiệu |
| `backend/app/services/context_engine/` | Nhận diện follow-up và quản lý/prune ngữ cảnh hội thoại |
| `backend/app/services/external_retrieval/` | Intent gate, provider web search, RSS, chuẩn hóa evidence và provenance; gồm `intent_gate.py`, `retrieval_service.py`, `multi_platform.py`, `evidence.py`, `evidence_context.py`, `brave_search.py`, `rss_feed.py`, `rss_sources.py` |
| `backend/app/services/product_trust/` | Đánh giá độ tin cậy nguồn và kiểm soát claim/evidence |
| `backend/app/services/output_validator/` | Kiểm tra cấu trúc và quy tắc đầu ra AI |
| `backend/app/services/voiceover/` | Làm sạch/kết xuất lời thoại, emotion cue và lưu metadata audio |
| `backend/app/services/voiceover/providers/` | Hợp đồng provider, Edge TTS, VieNeu và mock provider |
| `backend/app/services/stt/` | Điều phối speech-to-text và provider Vosk/Google/unavailable |
| `backend/app/services/voice_studio/` | Nhận đầu vào video và trích xuất audio cho STT |
| `backend/app/services/voice_conversion/` | Chuyển giọng, quản lý reference audio, probe và Seed-VC provider |
| `backend/app/services/media/` | Nghiệp vụ tạo/chỉnh sửa media, job, versioning và xử lý video; UI/API tạo mới hiện bị khóa |
| `backend/app/services/trend_report_service.py`, `trend_report_analysis.py` | Thu thập RSS, phân tích xác định và lưu/đọc history; UI RSS/Trend đang ẩn |
| `backend/app/services/trend_intelligence/`, `trend_monitor_service.py`, `trend_alert_service.py` | Logic monitor/snapshot/alert còn trong backend; không hàm ý scheduler đang chạy |
| `backend/app/services/learning_dataset/` | Phân loại và ghi dữ liệu học theo cơ chế riêng |
| `backend/app/services/knowledge_base/` | Quản lý truy xuất knowledge nội bộ |
| `backend/app/services/product_aware/`, `platform_intelligence/`, `multimodal/` | Ngữ cảnh sản phẩm, quy tắc nền tảng và xử lý đa phương thức |
| `backend/app/services/auth_service.py`, `user_service.py`, `session_service.py`, `google_auth_service.py` | Nghiệp vụ tài khoản, phiên và đăng nhập Google |
| `backend/app/services/email_service.py`, `email_verification_service.py`, `password_reset_service.py` | Email xác minh và khôi phục tài khoản |
| `backend/app/services/brand_service.py`, `campaign_service.py`, `dashboard_service.py`, `template_service.py` | Nghiệp vụ thương hiệu, chiến dịch, dashboard và mẫu |
| `backend/app/services/saved_content_service.py`, `content_document_service.py`, `content_activity_service.py`, `content_evaluation_service.py`, `content_variant_service.py`, `content_tool_utils.py` | Lưu, chỉnh sửa, đánh giá và tạo biến thể nội dung |
| `backend/app/services/file_storage.py`, `upload_service.py` | Lưu file và xử lý upload |

### Backend: migration

Mỗi file dưới đây là một revision riêng trong `backend/alembic/versions/`:

| Revision/file | Vai trò |
| --- | --- |
| `20260727_0001_initial_schema.py` | Các bảng lõi ban đầu |
| `20260727_0002_ad_templates.py` | Mẫu quảng cáo và yêu thích |
| `20260727_0003_google_auth.py` | Trường liên kết Google OAuth |
| `20260727_0004_password_reset.py` | Token đặt lại mật khẩu |
| `20260727_0005_email_verification_sessions.py` | Token xác minh email và phiên người dùng |
| `20260727_0006_brand_profiles.py` | Hồ sơ, tài sản và kiểm tra thương hiệu |
| `20260727_0007_content_editor_versions.py` | Tài liệu editor và version |
| `20260727_0008_campaign_primary_index.py` | Ràng buộc nội dung chính của campaign |
| `20260727_0009_platform_names.py` | Tên nền tảng tùy chỉnh ở nội dung |
| `20260727_0010_default_platform_name.py` | Nền tảng mặc định tùy chỉnh của user |
| `20260727_0011_campaign_platform_name.py` | Tên nền tảng tùy chỉnh cho campaign |
| `20260727_0012_media_assets.py` | Metadata asset media |
| `20261001_0013_video_asset_metadata.py` | Metadata video asset |
| `20261001_0014_media_jobs.py` | Bản ghi job media |
| `20261001_0015_media_asset_roots.py` | Liên kết nguồn/gốc asset media |
| `20261001_0016_media_edit_requests.py` | Yêu cầu chỉnh sửa media |
| `20261003_0017_voiceover_audio_ownership.py` | Owner và liên kết message cho audio voiceover |
| `20261005_0018_trend_report_evidence_store.py` | Evidence và claim của report |
| `20261005_0019_trend_report_source_statuses.py` | Trạng thái từng nguồn RSS/retrieval |
| `20261006_0020_product_trust_policies.py` | Chính sách tin cậy nguồn |
| `20261006_0021_trend_monitor_foundation.py` | Monitor và snapshot |
| `20261006_0022_trend_alert_engine.py` | Bản ghi alert và trạng thái |
| `20261006_0023_advertising_angles.py` | Góc quảng cáo và brief |
| `20261006_0024_insight_campaign_metrics.py` | Snapshot chỉ số chiến dịch |
| `20261006_0025_trend_report_history_soft_delete.py` | Xóa mềm history report |

### Frontend: entry point và client API

| File | Vai trò |
| --- | --- |
| `frontend/src/main.jsx` | Mount React và providers |
| `frontend/src/App.jsx` | Root component |
| `frontend/src/routes/AppRoutes.jsx`, `routes/index.js` | Khai báo route của ứng dụng |
| `frontend/src/layouts/ChatLayout/ChatLayout.jsx` | Khung trang chat |
| `frontend/src/layouts/WorkspaceLayout/WorkspaceLayout.jsx` | Khung các trang workspace |
| `frontend/src/pages/Chat/Chat.jsx` | Màn hình chat và kết nối các panel chính |
| `frontend/src/context/AuthContext.jsx`, `ThemeContext.jsx` | Trạng thái xác thực và giao diện |
| `frontend/src/hooks/useChat.js` | State và thao tác chat/conversation |
| `frontend/src/services/api/axios.js` | Axios instance, base URL và xử lý request chung |
| `frontend/src/services/api/authApi.js`, `userApi.js` | API xác thực, hồ sơ và cài đặt người dùng |
| `frontend/src/services/api/chatApi.js`, `conversationApi.js` | API tin nhắn/streaming và hội thoại |
| `frontend/src/services/api/brandApi.js`, `campaignApi.js`, `dashboardApi.js` | API thương hiệu, chiến dịch và dashboard |
| `frontend/src/services/api/contentEditorApi.js`, `contentToolsApi.js`, `savedContentApi.js` | API editor, công cụ nội dung và thư viện lưu |
| `frontend/src/services/api/templateApi.js` | API mẫu quảng cáo |
| `frontend/src/services/api/voiceoverApi.js`, `uploadApi.js` | API Voice Studio/STT và upload |
| `frontend/src/services/api/mediaApi.js` | API media; giữ client nhưng tạo mới đang bị khóa |
| `frontend/src/services/api/trendReportApi.js` | API RSS/Trend; giữ client nhưng giao diện truy cập tạm ẩn |
| `frontend/src/services/api/axios.js` | Client HTTP chung, cấu hình base URL và middleware |
| `frontend/src/services/storage/tokenStorage.js` | Lưu/đọc token xác thực phía client |

### Frontend: component, trang và tiện ích

| File/thư mục | Vai trò |
| --- | --- |
| `frontend/src/components/chat/ChatInput/` | Nhập nội dung, brief, nền tảng, thương hiệu và tệp đính kèm |
| `frontend/src/components/chat/MessageList/`, `MessageBubble/`, `MessageActions/` | Hiển thị lịch sử chat, message, attachment và thao tác message |
| `frontend/src/components/chat/Sidebar/`, `MobileSidebar/`, `SidebarDrawer/` | Danh sách, tìm kiếm và điều hướng conversation |
| `frontend/src/components/chat/Header/` | Tiêu đề hội thoại, export và thao tác header |
| `frontend/src/components/chat/AdBriefForm/`, `PromptSelector/`, `VariantGeneratorModal/` | Brief quảng cáo, chọn prompt và tạo biến thể |
| `frontend/src/components/chat/SavedContentPanel/`, `ContentScorePanel/` | Nội dung đã lưu và thông tin đánh giá |
| `frontend/src/components/chat/VoiceoverModal/` | Luồng UI nhập text/file, STT, chọn voice và audio result |
| `frontend/src/components/chat/MediaStudio/MediaStudio.jsx` | UI Media Studio; hiện hiển thị “Đang phát triển” và khóa thao tác tạo mới |
| `frontend/src/components/chat/TrendReportPanel/` | UI report RSS còn trong source; không có lối truy cập chính trong giao diện hiện tại |
| `frontend/src/components/navigation/AppNavigation/navigationItems.js`, `AppNavigation.jsx` | Khai báo và render menu điều hướng |
| `frontend/src/components/auth/` | Protected route, nhập mật khẩu/OTP, Google login và màn hình khôi phục |
| `frontend/src/components/brand/`, `campaign/`, `templates/`, `dashboard/`, `editor/`, `settings/` | Component theo miền thương hiệu, chiến dịch, mẫu, thống kê, editor và cài đặt |
| `frontend/src/pages/` | Các màn hình route: Chat, Dashboard, Campaigns, CampaignDetail, Brands, Library, ContentEditor, Templates, Settings, Profile và xác thực |
| `frontend/src/utils/` | Helper thuần cho validation, export, editor, nội dung, media và trạng thái report |
| `frontend/src/styles/`, `frontend/src/index.css` | CSS token, reset, theme và kiểu toàn cục |
| `frontend/src/constants/api.js`, `platforms.js` | Hằng số API và nền tảng nội dung |

Các file `.css` nằm cạnh component/page định nghĩa cách trình bày tương ứng; `index.js` trong từng thư mục thường là module re-export. Danh sách component con thay đổi thường xuyên nên xem trực tiếp thư mục khi cần tìm file chi tiết.

### Tài liệu và test

| File/thư mục | Vai trò |
| --- | --- |
| `docs/00-tong-quan-he-thong.md` | Tổng quan sản phẩm và ranh giới hệ thống |
| `docs/01-chuc-nang-he-thong.md` | Danh mục chức năng và trạng thái |
| `docs/02-luong-xu-ly-ai.md` | Luồng xử lý chat/AI |
| `docs/03-co-so-du-lieu.md` | Database runtime, 34 bảng, quan hệ và migration |
| `docs/04-api-va-frontend.md` | Kết nối API và giao diện |
| `docs/05-trien-khai-va-van-hanh.md` | Chạy và vận hành hệ thống |
| `docs/06-quy-uoc-dong-bo-tai-lieu.md` | Quy ước cập nhật tài liệu |
| `docs/07-huong-dan-su-dung-he-thong.md` | Hướng dẫn người dùng |
| `docs/08-vai-tro-cac-chuc-nang.md` | Vai trò các miền chức năng |
| `docs/09-voice-studio-audio-transform-plan.md` | Kế hoạch/chú giải mở rộng xử lý audio |
| `docs/10-adgen-ai-capstone-final-report.md` | Báo cáo đồ án tổng kết |
| `backend/tests/` | Unit/API/integration tests backend theo từng domain; ví dụ `test_database_bootstrap.py`, `test_media_api.py`, `test_voiceover_api.py` |
| `frontend/tests/` | Test frontend cho API contract, utility và component behavior; ví dụ `mediaStudioAvailability.test.js`, `voiceoverModalContract.test.js` |
| `backend/smoke/` | Script smoke cục bộ cho luồng voiceover |

`backend/checkpoints/`, file database cục bộ, model cache, upload và audio/video được sinh ra là dữ liệu runtime hoặc tài sản model; không phải schema hay mã nguồn. File `.env` thực không được liệt kê và giá trị bí mật không đưa vào tài liệu.

## Maintenance note

Đây là cây điều hướng có chọn lọc, không phải bản dump mọi file CSS, test, asset và cache. Mỗi file được liệt kê có vai trò kèm theo; cập nhật khi thêm/xóa miền chức năng, API boundary, provider, migration head hoặc vị trí test.

Ghi chú đồng bộ (14/10/2026):

- Revision mới nhất trong source migration là `20261006_0025`; trạng thái database đang chạy phải được xác định từ môi trường runtime.
- Voice Studio đi qua `frontend/src/components/chat/VoiceoverModal/`, API `voiceover.py`/`stt.py`/`video_stt.py`/`voice_conversion.py` và các service `voiceover/`, `stt/`, `voice_studio/`, `voice_conversion/`.
- `backend/checkpoints/` có thể chứa cache/trọng số model tải về. Đây là dữ liệu model lớn, không phải source code; không xóa hoặc đưa vào Git chỉ vì chúng xuất hiện trong cây máy cá nhân.
- RSS/Trend Report: giao diện truy cập đã tạm ẩn; component, API, service, model và lịch sử vẫn được giữ trong source/database.
- Media Studio: giao diện mang trạng thái “Đang phát triển”; backend chặn thao tác tạo mới theo cấu hình hiện tại. Provider, endpoint, model và lịch sử vẫn được giữ.

## Luồng chính giữa các file

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

### Luồng Voice Studio

- frontend/src/components/chat/VoiceoverModal/: UI text/file source, transcript review, chọn giọng, tốc độ, emotion, reference file và audio result.
- frontend/src/services/api/voiceoverApi.js: client của clean, STT, TTS, reference voice và direct conversion.
- backend/app/api/voiceover.py: endpoint clean/generate/audio và persistence ownership.
- backend/app/api/stt.py, video_stt.py: nhận dạng audio/video.
- backend/app/api/voice_conversion.py: endpoint chuyển giọng trực tiếp.
- backend/app/services/voiceover/: script cleaner, emotion cue, Edge TTS, VieNeu-TTS, output validation và persistence.
- backend/app/services/stt/: provider factory, Vosk, Google adapter và fail-closed provider.
- backend/app/services/voice_studio/: probe video và extraction audio.
- backend/app/services/voice_conversion/: audio probe, reference manager, Seed-VC converter và provider factory.
- backend/app/assets/ref_audios/ngoc_huyen_ref.wav: audio mẫu/reference hiện có trong repository.

### Điều hướng frontend

- frontend/src/components/navigation/AppNavigation/navigationItems.js: danh sách menu dùng chung, tách khỏi component để tránh lỗi Fast Refresh/ESLint.
- frontend/src/components/navigation/AppNavigation/AppNavigation.jsx: render menu điều hướng.
- `navigationItems.js` là nguồn danh sách mục điều hướng; `AppNavigation.jsx` hiển thị các mục đó.

### Test và dữ liệu runtime

- backend/tests/: test unit/API/integration cho auth, database, chat lifecycle, retrieval, media, STT, voiceover, emotion và voice conversion.
- frontend/tests/: contract/unit tests cho UI utilities, content workflow và Voice Studio.
- backend/checkpoints/, virtual environments, model caches, uploads và generated audio không được xem là source tree; chúng cần được quản lý riêng, không tự động xóa khi dọn source.

## Update rule

Khi thêm endpoint, service boundary, provider, migration head, file reference hoặc nhóm test mới, cập nhật đồng thời docs/00-tong-quan-he-thong.md, docs/02-luong-xu-ly-ai.md, docs/03-co-so-du-lieu.md, docs/10-adgen-ai-capstone-final-report.md và tài liệu này.
