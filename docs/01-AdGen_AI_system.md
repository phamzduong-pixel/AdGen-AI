# AdGen AI — Tổng quan hệ thống

> Cập nhật: 02/10/2026
>
> Trạng thái: Chat text và các phase implementation của Plan 09 đã được cập nhật theo source hiện tại; real media runtime vẫn còn blocker môi trường/provider.

## 1. Phạm vi hệ thống

AdGen AI là ứng dụng hỗ trợ tạo, chỉnh sửa, đánh giá và quản lý nội dung quảng cáo bằng AI. Người dùng có thể bắt đầu từ yêu cầu tự nhiên, brief, template hoặc nội dung đã lưu; sau đó tiếp tục chỉnh sửa trong hội thoại, tạo biến thể, đánh giá chất lượng, lưu nội dung theo chiến dịch và tạo voiceover.

Hệ thống vẫn giữ chat text làm luồng chính, đồng thời đã có implementation cho Image MVP, Technical Video Editing, AI Video Generation foundation và Conversational Video Editing theo [09-ke-hoach-tao-anh-video.md](09-ke-hoach-tao-anh-video.md). Các contract, mock/SQLite tests và UI đã có; real FFmpeg/FFprobe, PostgreSQL concurrency và real Gemini video provider chưa được xác minh trong môi trường hiện tại.

## 2. Kiến trúc logic hiện tại

\`\`\`text
┌────────────────────────────────────────────────────────────┐
│ React 19 + Vite frontend                                   │
│ Pages / components / hooks / API clients / chat UI         │
└─────────────────────┬──────────────────────────────────────┘
                      │ HTTP JSON, multipart upload, text stream
                      ▼
┌────────────────────────────────────────────────────────────┐
│ FastAPI backend                                            │
│ Routers → schemas → services → SQLAlchemy models           │
│ Auth/JWT, ownership checks, validation, local file storage  │
└──────────────┬──────────────────┬──────────────────────────┘
               │                  │
               ▼                  ▼
┌────────────────────────┐  ┌────────────────────────────────┐
│ SQLite / PostgreSQL     │  │ Gemini + AI pipeline             │
│ Alembic migrations      │  │ prompts, context, intelligence, │
│ conversation and files  │  │ validation, learning dataset    │
└────────────────────────┘  └────────────────────────────────┘
\`\`\`

### Các lớp chính

- Frontend chịu trách nhiệm giao diện, trạng thái hội thoại, form, preview, upload và gọi API.
- Backend chịu trách nhiệm xác thực, phân quyền, xử lý nghiệp vụ, gọi Gemini, lưu dữ liệu và streaming.
- Database lưu người dùng, conversation, message, brief, brand, campaign, template, nội dung đã lưu và file upload.
- AI pipeline ghép context, prompt, lịch sử hội thoại và dữ liệu thương hiệu/sản phẩm trước khi gửi yêu cầu đến Gemini.
- Alembic quản lý migration; không xóa dữ liệu cũ chỉ vì một giá trị legacy không còn xuất hiện ở giao diện mới.
### Media runtime hiện tại

- `MediaAsset` lưu image/video, metadata, trạng thái, ownership, conversation, `parent_asset_id`, `root_asset_id` và `version_number`.
- Image flow dùng provider adapter Gemini, lưu file local, preview/download, reference image và tạo asset mới khi edit.
- Video flow hỗ trợ upload/register, trim, aspect/crop, text/CTA overlay, subtitle, volume/mute và merge qua controlled processor contract.
- Media Studio hỗ trợ chọn source, cấu hình operation, preview/download output và giữ source version cũ.
- Conversational video editing dùng deterministic parser, structured plan, preflight validation, allowlist operation, partial recovery và durable idempotency cho endpoint `/conversational-edits`.
- AI video generation dùng `GeminiVideoProvider`, `MediaJob`, submit/poll/download và validation; provider thật hiện bị chặn bởi quota/access.
- Các test media hiện dùng mock/fake processor hoặc SQLite; chúng không thay thế real FFmpeg/FFprobe/Gemini runtime verification.

## 3. Cấu trúc source chính

### Frontend

- \`frontend/src/pages/\`: các màn hình auth, chat, dashboard, library, template, brand, campaign, editor, profile và settings.
- \`frontend/src/components/\`: UI dùng lại và các nhóm auth, chat, campaign, brand, editor, dashboard, template.
- \`frontend/src/hooks/\`: hook cho chat, conversation, brand, campaign, editor, dashboard, template và streaming.
- \`frontend/src/services/api/\`: các client API theo domain; Axios dùng \`VITE_API_URL\` và JWT.
- \`frontend/src/context/\`: authentication và theme/context dùng chung.
- \`frontend/src/utils/\`: storage, markdown, download, date, copy và các utility khác.
- \`frontend/src/layouts/\`: layout dùng chung của ứng dụng.

### Backend

- \`backend/app/api/\`: HTTP routers cho auth, messages, conversations, uploads, templates, brands, campaigns, saved contents, evaluation, variants, voiceover và các domain khác.
- \`backend/app/schemas/\`: Pydantic schemas, là hợp đồng request/response của API.
- \`backend/app/models/\`: SQLAlchemy models và quan hệ dữ liệu.
- \`backend/app/services/\`: AI, authentication, storage, conversation, content, brand, campaign, voiceover và các service hỗ trợ.
- \`backend/app/prompts/\`: system prompt, prompt theo platform và prompt chuyên biệt.
- \`backend/app/services/context_engine/\`: các thành phần xử lý context/follow-up/brief; tồn tại trong source nhưng không phải toàn bộ đều được gọi trực tiếp ở luồng chat chính.
- \`backend/app/services/knowledge_base/\`, \`platform_intelligence/\`, \`product_aware/\`, \`trend_intelligence/\`, \`output_validator/\`, \`learning_dataset/\`: các lớp tri thức, kiểm tra output và ghi dữ liệu phục vụ đánh giá.
- \`backend/app/database/\`: engine, session và tương thích SQLite legacy.
- \`backend/app/core/\`: settings, security và tiện ích dùng chung.
- \`backend/alembic/\`: migration database hiện có.
- \`backend/tests/\`: test backend.

## 4. Luồng AI hiện tại

### 4.1. Luồng tạo nội dung không stream

\`\`\`text
Request /messages
    → xác thực user và conversation
    → đọc brief, brand, product, platform và lịch sử
    → ghép system prompt + platform prompt + context
    → gọi Gemini generate_content()
    → output validation và sanitize
    → ghi learning dataset
    → lưu assistant message
    → trả response JSON
\`\`\`

### 4.2. Luồng tạo nội dung stream

\`\`\`text
Request /messages/stream
    → xác thực và chuẩn bị context
    → gọi Gemini generate_content_stream()
    → gửi từng text chunk qua StreamingResponse
    → ghép full response
    → lưu assistant message
\`\`\`

Luồng stream hiện ưu tiên phản hồi nhanh. Theo hiện trạng source, stream chưa chạy đầy đủ output validation và learning-dataset logging giống luồng không stream; đây là điểm cần xử lý riêng nếu muốn hai chế độ hoàn toàn đồng nhất.

### 4.3. Prompt và context

Prompt được xây dựng từ các lớp sau:

1. System prompt và quy tắc an toàn.
2. Prompt theo nền tảng được chọn.
3. Brief và yêu cầu hiện tại.
4. Brand/product context nếu người dùng đã cấu hình.
5. Platform intelligence, knowledge base và trend intelligence khi luồng tương ứng sử dụng.
6. Lịch sử hội thoại và các file đính kèm phù hợp.

Gemini nhận message dạng user/model. File ảnh, video và PDF có thể được đưa vào context dưới dạng part; file văn bản/tài liệu được giới hạn lượng nội dung đọc vào prompt.

## 5. Nền tảng nội dung

Danh sách nền tảng mới cho nội dung tạo mới chỉ gồm:

- Facebook.
- TikTok.
- Instagram.
- Shopee.
- Google Ads.
- Khác.

Giao diện có thể ưu tiên hiển thị Facebook, TikTok, Shopee và đưa các lựa chọn còn lại vào phần mở rộng tùy layout.

### Lựa chọn “Khác”

- Người dùng phải nhập tên nền tảng hoặc nơi đăng nội dung, ví dụ \`Zalo OA\` hoặc \`website của cửa hàng\`.
- Backend cần kiểm tra độ dài, chuẩn hóa khoảng trắng và truyền giá trị này vào context tạo nội dung.
- Giá trị này chỉ là dữ liệu đầu vào, không được ghi đè system prompt hoặc quy tắc an toàn.
- Nếu hệ thống không có thông tin riêng về nền tảng đó, AI tạo nội dung quảng cáo chung phù hợp với brief, không tự khẳng định quy định hay giới hạn chưa được kiểm chứng.

### Giá trị legacy

Landing Page, Email, SEO, Slogan, Viết lại và Tóm tắt không còn là nền tảng của luồng tạo nội dung mới. \`Viết lại\` và \`Tóm tắt\` vẫn có thể tồn tại dưới nhóm thao tác chỉnh sửa nội dung.

Các giá trị cũ trong conversation, message, template hoặc dữ liệu đã lưu không bị xóa. Chúng cần được đọc và hiển thị tương thích; không được đưa trở lại danh sách nền tảng mới nếu không thuộc phạm vi hỗ trợ hiện hành.

## 6. Upload và multimodal

### Upload hiện tại

Upload service hỗ trợ các nhóm file:

- Tài liệu: \`.docx\`, \`.pdf\`, \`.txt\`.
- Ảnh: \`.jpeg\`, \`.jpg\`, \`.png\`, \`.webp\`.
- Video: \`.mp4\`, \`.mov\`, \`.webm\`.

API upload chính:

- \`POST /uploads/{conversation_id}\`: upload file cho conversation.
- \`GET /uploads/{conversation_id}\`: lấy danh sách file.
- \`GET /uploads/file/{file_id}/download\`: tải file khi có quyền.
- \`DELETE /uploads/file/{file_id}\`: xóa file khi có quyền.

Video upload hiện có giới hạn dung lượng riêng và file được lưu bằng local file storage. Asset video upload là source cho Technical Video Editing; mỗi edit tạo asset/version mới và không ghi đè source.

### Multimodal scaffold

\`backend/app/services/multimodal/\` đã định nghĩa:

- Modality text, image, video và audio.
- Task type text-to-text, image-to-text, video-to-text, text-to-image, text-to-video và video-to-edited-video.
- Lệnh chỉnh sửa dự kiến như trim, đổi tỷ lệ, thêm CTA, phụ đề, audio enhancement và hook.
- Payload gồm prompt, media assets, edit instructions, target modality và generation options.

Các contract multimodal vẫn là lớp mô tả chung. Media API/provider/service thực tế đã được triển khai riêng cho Image MVP, Technical Video Editing, AI Video Generation foundation và Conversational Video Editing; không đồng nghĩa mọi task trong scaffold đều đã có real provider/runtime.

## 7. Các chức năng nghiệp vụ hiện có

- Đăng ký, đăng nhập, JWT và phân quyền người dùng.
- Chat tạo nội dung và mở lại conversation.
- Lịch sử hội thoại, tìm kiếm và tiếp tục chỉnh sửa.
- Template và brief cho các nhu cầu quảng cáo.
- Brand profile, product context và campaign.
- Lưu nội dung, thư viện và tải nội dung.
- Đánh giá nội dung, tạo biến thể và chỉnh sửa nội dung.
- Upload file đính kèm.
- Tạo/chỉnh sửa ảnh trong Media Studio, reference image, preview/download và version lineage.
- Technical Video Editing: upload/register, trim, crop/aspect, text/CTA, subtitle, volume/mute và merge.
- AI Video Generation foundation với Gemini Veo job lifecycle và frontend polling/recovery.
- Conversational Video Editing với structured operations, preflight, partial execution recovery và idempotency key.
- Voiceover/TTS thông qua provider adapter.
- Dashboard và settings.
- Giao diện auth login/register theo hướng glassmorphism, dùng màu chủ đạo HyperCobalt \`#0038FF\` và Powder Sky \`#D6E3FF\`.

Các chức năng UI có thể được mở rộng nhưng phải giữ API contract, quyền sở hữu và dữ liệu cũ.

## 8. Dữ liệu và lưu trữ

### Database

- SQLite được dùng cho local/test và database runtime hiện tại.
- PostgreSQL được hỗ trợ cho production.
- Alembic quản lý migration.
- \`backend/adgen_dev.db\` là database SQLite runtime local hiện đang được cấu hình sử dụng; \`backend/chatbot.db\` là database legacy được giữ nguyên để bảo toàn dữ liệu.
- \`backend/adgen.db\` được giữ nguyên theo yêu cầu tương thích; chưa kết luận và chưa xóa trong cleanup.

### File storage

- File upload hiện được lưu dưới \`backend/uploads/\`.
- \`backend/.env\` và \`frontend/.env\` được giữ nguyên, không expose secrets.
- Uploaded user files không bị xóa trong cleanup.
- Production cần persistent volume hoặc object storage để tránh mất file khi redeploy.

### Dữ liệu media

\`MediaAsset\` được dùng cho vòng đời image/video, còn \`MediaJob\` dùng cho AI video generation bất đồng bộ. \`MediaEditRequest\` lưu idempotency/replay state cho conversational edit. \`MediaVersion\` và \`MediaOperation\` chưa phải các model độc lập; version lineage hiện được biểu diễn bằng \`MediaAsset.parent_asset_id\`, \`root_asset_id\`, \`version_number\` và \`operation\`.

File gốc cần được giữ lại; mỗi lần chỉnh sửa tạo version mới. Unique constraint bảo vệ version trong cùng user/conversation/kind/root lineage. PostgreSQL concurrency vẫn cần runtime verification.

## 9. Bảo mật và quy tắc an toàn

- JWT và ownership check được dùng để bảo vệ conversation, message, file và nội dung người dùng.
- Không để custom platform, brief hoặc prompt người dùng ghi đè system prompt.
- Không tự bịa giá, ưu đãi, số liệu, chứng nhận hoặc thông tin sản phẩm.
- File download/delete phải kiểm tra quyền sở hữu.
- Lệnh chỉnh sửa video phải đi qua allowlist; không cho AI chạy shell command hoặc filesystem path tùy ý.
- Conversational request phải chuyển thành structured operation trước khi backend thực thi.
- Backend kiểm tra ownership, conversation scope, media kind, completed status, file/MIME/size/duration và output metadata.
- Idempotency key được scope theo user/conversation cho conversational video edit; key khác nhau vẫn là request độc lập.
- Cần tiếp tục bổ sung quota/rate limit/chi phí production cho media generation.

## 10. Công nghệ và runtime

| Thành phần | Công nghệ / hiện trạng |
| --- | --- |
| UI | React 19, React Router, React Markdown |
| Build frontend | Vite 8, Node.js 20+ |
| API | FastAPI 0.139, Uvicorn |
| ORM/migration | SQLAlchemy 2, Alembic |
| Auth | JWT (\`python-jose\`), bcrypt, Google Identity Services tùy chọn |
| AI hiện tại | Google Gen AI SDK, Gemini 2.5 Flash cho chat; Gemini image adapter và Gemini Veo adapter cho media |
| Database | SQLite local/test, PostgreSQL production |
| Upload | Python multipart và local file storage |
| Realtime | Fetch streaming ở frontend và \`StreamingResponse\` ở backend |
| Media generation | Image provider và Gemini Veo provider đã tích hợp; real provider verification còn thiếu |
| Video processing | Controlled FFmpeg processor đã tích hợp trong backend image/container; local Windows chưa có FFmpeg/FFprobe |
| Deployment | Docker Compose hoặc Render Blueprint theo cấu hình dự án |

## 11. Khởi động và entry point

Backend khởi tạo tại \`backend/app/main.py\`: load settings, kiểm tra cấu hình, khởi tạo/tương thích SQLite, seed system templates, cấu hình CORS và include routers. Endpoint cơ bản gồm \`GET /\` và \`GET /health\`.

Local runtime dự kiến:

- Backend: \`http://localhost:8000\`.
- Frontend: \`http://localhost:5173\`.

Docker Compose chạy frontend qua Nginx, backend và PostgreSQL với named volumes khi môi trường được cấu hình đầy đủ.

## 12. Cleanup filesystem gần nhất

Đã thực hiện cleanup theo phạm vi được phê duyệt:

- Xóa các generated artifact có thể tạo lại: \`frontend/dist/\`, cache pytest và các artifact dependency đã không bị khóa.
- Xóa hai CSS legacy ở root và \`backend/app/services/chat_service.py\` sau khi kiểm tra không còn reference.
- Một số binary trong \`frontend/node_modules/\` và \`backend/venv/\` có thể còn nếu đang bị process khóa; không tự dừng process để cưỡng chế xóa.
- Giữ nguyên source, migration, test, database, uploads, \`.env\` và các scaffold/utility đã được yêu cầu bảo toàn.
- Không commit, push, refactor hoặc thay đổi logic nghiệp vụ trong cleanup.

Chi tiết được ghi tại [07-quy-uoc-dong-bo-tai-lieu.md](07-quy-uoc-dong-bo-tai-lieu.md). Cây thư mục hiện tại được theo dõi tại [PROJECT_TREE.md](PROJECT_TREE.md).

## 13. Tài liệu liên quan

- [03-luong-xu-ly-ai.md](03-luong-xu-ly-ai.md): luồng xử lý AI hiện tại và các điểm khác nhau giữa stream/non-stream.
- [07-quy-uoc-dong-bo-tai-lieu.md](07-quy-uoc-dong-bo-tai-lieu.md): quy ước đồng bộ tài liệu và nhật ký cleanup.
- [09-ke-hoach-tao-anh-video.md](09-ke-hoach-tao-anh-video.md): kế hoạch tạo ảnh, tạo video và chỉnh sửa video.
- [10-tien-do-media-mvp.md](10-tien-do-media-mvp.md): tiến độ Image MVP và media implementation.
- [11-environment-test-plan.md](11-environment-test-plan.md): hướng dẫn xác minh Docker/FFmpeg/Gemini runtime.
- [12-plan-09-final-audit.md](12-plan-09-final-audit.md): final audit Plan 09.
- [13-versioning-partial-recovery.md](13-versioning-partial-recovery.md): versioning và partial execution recovery.
- [14-runtime-readiness-audit.md](14-runtime-readiness-audit.md): kết quả runtime readiness hiện tại.
- [PROJECT_TREE.md](PROJECT_TREE.md): cây thư mục và file được ghi nhận tại thời điểm cập nhật.

## 14. Giới hạn và việc cần làm tiếp

- Chưa có refresh token.
- Rate limit OTP còn phụ thuộc memory của process; môi trường nhiều worker cần Redis hoặc reverse proxy.
- Local upload storage cần persistent volume/object storage khi triển khai production.
- SQLite phù hợp local/demo một instance; production nên dùng PostgreSQL.
- Cần rate limit/quota cho Gemini.
- Stream chưa đồng nhất hoàn toàn với non-stream về validation và learning dataset.
- Context engine có module hỗ trợ nhưng cần tiếp tục xác nhận/hoàn thiện wiring ở từng luồng.
- Real FFmpeg/FFprobe chưa được xác minh vì local Windows không có Docker/FFmpeg/FFprobe.
- Real Gemini Veo chưa được xác minh; smoke test trước đó bị `429 RESOURCE_EXHAUSTED`.
- PostgreSQL concurrent version allocation/idempotency chưa được chạy; test hiện tại là SQLite/session-level.
- Full Alembic chain còn blocker cũ tại migration `20260727_0008` do index đã tồn tại.
- Frontend chưa có React component integration harness cho partial recovery; utility tests và production build đã pass.
- `MediaVersion` và `MediaOperation` chưa tồn tại như model độc lập; version/operation hiện nằm trong `MediaAsset`.
- Dependency đã được cleanup nên môi trường local có thể cần cài lại trước khi chạy build/test; không tự cài dependency trong các task chỉ đọc hoặc cleanup.

Tài liệu này mô tả hiện trạng thực tế, phân biệt rõ chức năng đang chạy với scaffold hoặc kế hoạch tương lai. Khi source thay đổi ở các phần kiến trúc, API, schema, AI pipeline, platform hoặc runtime, file này cần được cập nhật cùng task tương ứng.


## 15. Trạng thái Plan 09 — 02/10/2026

### Đã hoàn thành về implementation

- Phase 1: Image Generation/Edit, MediaAsset, Gemini image adapter, reference image, ownership, preview/download và version preservation.
- Phase 2: Technical Video Editing backend/UI cho trim, aspect/crop, text overlay, CTA, subtitle, volume, mute và merge.
- Phase 3: AI Video Generation foundation với Gemini Veo adapter, MediaJob, submit/poll/download, validation và frontend recovery.
- Phase 4: Conversational Video Editing với deterministic parser, structured plan, preflight validation, allowlist, partial execution recovery và idempotency key.
- Versioning dùng `root_asset_id`, `parent_asset_id`, `version_number` và unique lineage constraint; source không bị overwrite.
- Targeted backend media/video tests, frontend tests và production build đã pass theo các checkpoint gần nhất.

### Chưa đủ điều kiện đóng Plan 09

- Real FFmpeg/FFprobe chưa chạy do môi trường local thiếu Docker/FFmpeg/FFprobe.
- Real Gemini Veo chưa xác minh do lần smoke test trước bị `429 RESOURCE_EXHAUSTED`.
- PostgreSQL concurrent version allocation/idempotency chưa được kiểm chứng.
- Full Alembic chain còn blocker migration cũ `20260727_0008`.
- Frontend component-level partial recovery chưa có integration harness tự động.

Vì vậy: `PLAN 09 IMPLEMENTATION = MOSTLY COMPLETE`, `PLAN 09 END-TO-END VERIFICATION = NOT COMPLETE`, `PLAN 09 = IN PROGRESS`.
