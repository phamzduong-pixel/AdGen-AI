# AdGen AI — Báo cáo tổng hợp hệ thống

> Cập nhật: 02/10/2026  
> Phạm vi: source code và kết quả kiểm thử hiện có trong repository  
> Trạng thái tổng thể: **Code local ổn định trong phạm vi đã kiểm tra; runtime provider và PostgreSQL vẫn cần xác minh riêng**.

## 1. Mục đích sản phẩm

AdGen AI là nền tảng hỗ trợ tạo, chỉnh sửa, đánh giá và quản lý nội dung quảng
cáo bằng Generative AI. Người dùng có thể làm việc qua hội thoại, brief quảng
cáo, template, thương hiệu, campaign, thư viện nội dung, trình chỉnh sửa phiên
bản, Media Studio và Voice Studio.

Luồng chính của sản phẩm:

```text
Người dùng → React UI → API FastAPI → Service/domain logic
                         ├─ SQLAlchemy → SQLite/PostgreSQL
                         ├─ Gemini/OpenAI image provider
                         ├─ Gemini video provider
                         ├─ Edge TTS provider
                         └─ Local file storage / media assets
```

## 2. Công nghệ và cấu trúc repository

| Thành phần | Công nghệ | Vị trí chính |
| --- | --- | --- |
| Frontend | React 19, Vite, Axios, React Router | `frontend/src/` |
| Backend | FastAPI, SQLAlchemy, Pydantic, JWT | `backend/app/` |
| AI text | Gemini service, prompt/context pipeline | `backend/app/services/ai_service.py`, `backend/app/prompts/` |
| AI image | Provider adapter Gemini/OpenAI | `backend/app/services/media/providers/` |
| AI video | Gemini Veo adapter và MediaJob | `backend/app/services/media/` |
| TTS | `edge-tts`, mock provider | `backend/app/services/voiceover/` |
| Database | SQLite local/test, PostgreSQL production mục tiêu | `backend/app/database/`, `backend/alembic/` |
| File storage | Local upload directory | `backend/uploads/`, storage/media services |
| Deployment | Dockerfile, Compose, Nginx, Render config | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `render.yaml` |

Các nhóm source quan trọng:

- `frontend/src/pages/`: màn hình đăng nhập, chat, dashboard, library, template,
  brand, campaign, editor, profile và settings.
- `frontend/src/components/chat/`: chat UI, MessageBubble, MediaStudio,
  VoiceoverModal, content tools và editor.
- `frontend/src/hooks/`: state và luồng chat, conversation, campaign, brand,
  template, content editor.
- `frontend/src/services/api/`: client API theo domain và streaming.
- `backend/app/api/`: router HTTP.
- `backend/app/schemas/`: request/response contract.
- `backend/app/models/`: SQLAlchemy models và quan hệ dữ liệu.
- `backend/app/services/`: nghiệp vụ, AI, media, auth, storage, voiceover.
- `backend/tests/` và `frontend/tests/`: kiểm thử tự động.

## 3. Chức năng sản phẩm

### Tài khoản và bảo mật

- Đăng ký và đăng nhập local bằng username/email và password.
- JWT bearer token, session tracking và logout theo session.
- Google login tùy chọn khi cấu hình Google Client ID.
- Xác minh email và khôi phục password bằng OTP SMTP.
- Đổi password làm vô hiệu hóa token cũ thông qua `token_version`.
- Route protected kiểm tra user ownership đối với conversation, file, brand,
  saved content và media asset.

### Chat và tạo nội dung

- CRUD conversation, đổi tên, ghim, lấy lịch sử và gửi message.
- Non-stream qua `POST /messages`.
- Streaming qua `POST /messages/stream` bằng Fetch/SSE-style response.
- Brief hỗ trợ sản phẩm, khách hàng, nhu cầu, platform, tone, ngôn ngữ và độ dài.
- Platform hiện gồm Facebook, TikTok, Instagram, Shopee, Google Ads và kênh tùy
  chỉnh.
- AI pipeline ghép system prompt, platform prompt, brief, lịch sử chat, brand
  context và dữ liệu sản phẩm trước khi gọi provider.

### Nội dung, template và campaign

- System template và custom template.
- Favorite template theo user.
- Lưu message vào thư viện và ghi content activity.
- Campaign CRUD, liên kết saved content và chọn primary content.
- Content document/version history, compare, restore và AI rewrite.
- Chấm điểm nội dung theo nhiều tiêu chí và tạo các biến thể A/B/C.
- Dashboard summary, hoạt động và platform usage.

### Upload và media

- Upload image, video, PDF và text có kiểm tra MIME, kích thước, quyền sở hữu.
- MediaAsset lưu loại media, trạng thái, metadata, owner, conversation và file path.
- Image generation/edit hỗ trợ reference image, tạo asset mới và giữ source cũ.
- Media Studio có preview, polling trạng thái, retry theo contract, download output.
- Video editing có trim, crop/aspect, text/CTA overlay, subtitle, volume/mute và merge.
- Conversational video edit dùng parser deterministic, structured plan, allowlist và
  preflight toàn bộ plan trước khi thực thi.

### Voice Studio

- Trích xuất và làm sạch script thoại.
- Chọn voice/language.
- Tổng hợp audio qua Edge TTS.
- Kiểm tra output non-empty và cleanup file tạm khi provider lỗi hoặc output không hợp lệ.
- Có mock provider để kiểm thử offline.

## 4. Generative AI và provider

### Text generation

Gemini là provider text chính trong `ai_service.py`. Prompt không được coi dữ liệu
người dùng là system instruction. Các claim về giá, chứng nhận, ưu đãi hoặc số liệu
không được tự bịa khi brief không cung cấp.

### Image generation

Provider được chọn bằng `IMAGE_PROVIDER`:

```dotenv
IMAGE_PROVIDER=gemini
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
OPENAI_IMAGE_MODEL=gpt-image-2.5-sunburst
```

API key chỉ đọc ở backend. Lỗi provider được chuẩn hóa theo code như
`RESOURCE_EXHAUSTED`, `INVALID_ARGUMENT`, `MODEL_NOT_FOUND`, `PERMISSION_DENIED`,
`UNAUTHENTICATED`, `PROVIDER_TIMEOUT`, `PROVIDER_ERROR` và `IMAGE_OUTPUT_MISSING`.
Frontend ánh xạ theo error code; HTTP 429 không có provider evidence không được tự
động kết luận là quota đã hết.

Real Gemini/OpenAI image call chưa được coi là PASS chỉ dựa trên mock tests.

### Video generation

Gemini Veo dùng `MediaJob` và flow submit → poll → download → validate → tạo
`MediaAsset`. Provider test dùng mock operation. Real Veo smoke test trước đó gặp
`429 RESOURCE_EXHAUSTED`, vì vậy real provider vẫn là **BLOCKED/UNVERIFIED**.

### TTS

`edge-tts` được khai báo trong `backend/requirements.txt` và import trì hoãn trong
provider. Unit/mock tests đã đạt; một lần tổng hợp tiếng Việt thực tế đã thành công
trong môi trường có dependency và file output được cleanup sau kiểm tra.

### Phương pháp AI đang áp dụng

Hệ thống kết hợp nhiều phương pháp, không phụ thuộc vào một prompt đơn lẻ:

1. **Phân loại mục đích và platform**: request được xác định theo loại nội dung,
   platform, ngôn ngữ, tone và mục tiêu trước khi chọn prompt chuyên biệt.
2. **Context engineering**: backend ghép system prompt, brief, lịch sử hội thoại,
   brand context, dữ liệu sản phẩm, template và attachment đã được kiểm tra quyền.
3. **Prompt specialization**: prompt được tách theo Facebook, TikTok, Instagram,
   Shopee, Google Ads, email, SEO, slogan, rewrite và các nghiệp vụ liên quan.
4. **Grounding theo dữ liệu người dùng**: thông tin giá, ưu đãi, chứng nhận,
   thông số và claim chỉ được dùng khi có trong brief/brand/product context; hệ
   thống không tự bịa dữ liệu thương mại.
5. **Output validation**: kết quả được kiểm tra cấu trúc, độ dài, field bắt buộc,
   nội dung rỗng và các quy tắc an toàn trước khi lưu hoặc trả về frontend.
6. **Structured editing**: yêu cầu chỉnh sửa nội dung/video được chuyển thành
   schema hoặc plan có allowlist, giới hạn tham số và preflight toàn bộ trước khi
   thực thi; user không truyền trực tiếp shell command hay filesystem path.
7. **Provider abstraction**: image/video/TTS dùng interface/provider adapter để
   thay provider, mock provider trong test và phân loại lỗi theo error code ổn định.
8. **Streaming và state tracking**: text chat có streaming; media generation dùng
   trạng thái queued/processing/completed/failed và lưu asset/version lineage.

Pipeline AI chuẩn:

```text
User request
  → normalize/validate request
  → resolve intent, platform, brief và brand context
  → load conversation history và attachment metadata
  → build specialized prompt / structured media plan
  → call provider adapter
  → classify provider/error response
  → validate output và cleanup temporary files
  → persist message, asset, version hoặc job state
  → stream/return result cho frontend
```

Các phương pháp trên đã được áp dụng trong code và được kiểm tra chủ yếu bằng
unit/API/mock tests. Real provider, quota, FFmpeg/FFprobe và PostgreSQL runtime
vẫn phải được xác minh riêng; không suy diễn các kết quả mock thành runtime PASS.

## 5. Luồng chat điển hình

1. Frontend tạo hoặc chọn conversation.
2. Người dùng nhập text/brief, chọn platform, template hoặc brand.
3. Frontend gửi request JSON hoặc stream request đến backend.
4. Backend xác thực JWT và kiểm tra ownership của conversation, brand, attachment.
5. User message được lưu.
6. Context engine dựng prompt từ brief, lịch sử, brand và platform.
7. AI provider trả text; backend validate output và lưu assistant message.
8. Frontend cập nhật bubble, có thể lưu, đánh giá, tạo variant, đưa vào campaign,
   export hoặc mở content editor.

Message user hiện được hiển thị bằng plain text với `white-space: pre-wrap` và
`text-align: left`. Message assistant được render Markdown và căn trái.

## 6. Database và schema safety

### Runtime hiện tại

- `backend/app/database/schema_manifest.py`: canonical manifest độc lập với
  `Base.metadata`.
- `backend/app/database/schema_validator.py`: validator chỉ đọc, so sánh bảng,
  cột, kiểu, nullable, default, primary key, FK, unique, index và check constraint.
- `backend/app/database/schema_state.py`: phân loại database rỗng, unmanaged,
  drift, stale marker, managed canonical và mismatch.
- `backend/app/database/bootstrap.py`: bootstrap explicit cho database rỗng; chỉ
  ghi `alembic_version` sau khi validation PASS.
- `backend/app/database/legacy_reconciliation.py`: inspect-only, không stamp,
  không repair, không đổi dữ liệu.
- `backend/app/database/database.py`: `initialize_database()` fail-closed; chỉ
  cho backend startup khi schema canonical và revision hợp lệ.
- Docker entrypoint không tự chạy migration.

### Database local hiện tại

Database đang được cấu hình cho local development:

```text
backend/adgen_dev.db
```

Database mới đã được bootstrap và xác minh:

```text
schema_status = PASS
state         = MANAGED_CANONICAL_SCHEMA
revision      = 20261001_0016
```

Database cũ `backend/chatbot.db` được giữ nguyên. Nó có marker
`20260727_0008` nhưng schema mismatch, nên runtime guard từ chối khởi động trên
file này để bảo vệ dữ liệu. Không được tự ý stamp hoặc chạy repair trên file đó.

### Migration history cần lưu ý

Chuỗi `20260727_0001` đến `20261001_0016` còn vấn đề lịch sử:

- `0001` gọi `Base.metadata.create_all()` và tạo trước một phần schema thuộc các
  revision sau.
- `0008` có thể tạo trùng index `uq_content_documents_campaign_primary`.
- Các revision sau còn nguy cơ duplicate column/table/index tùy trạng thái schema.
- SQLite disposable đã tái hiện lỗi từ database rỗng tại `0008`.
- Không rewrite migration history vì chưa xác định được database nào đã dùng revision.

Đường hỗ trợ local hiện tại là bootstrap explicit. PostgreSQL disposable và chiến
lược migration legacy production vẫn cần checkpoint riêng.

## 7. Cách chạy local

### Backend database mới

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m app.database.bootstrap --confirm-empty
uvicorn app.main:app --reload
```

Bootstrap chỉ được chạy khi `DATABASE_URL` trỏ đến database rỗng và disposable.
Không chạy trên database production hoặc file có dữ liệu cần bảo toàn.

### Kiểm tra legacy database

```powershell
cd backend
python -m app.database.legacy_reconciliation
```

Đây là lệnh chỉ đọc. Kết quả `MISMATCH` hoặc `BLOCKED` cần review và backup trước
khi thiết kế repair riêng.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend đọc backend URL từ `VITE_API_URL` trong `frontend/.env`.

### Health check

```text
GET http://localhost:8000/health
→ {"status":"ok","service":"adgen-ai-api"}
```

## 8. Cấu hình môi trường

Không ghi secret thật vào tài liệu hoặc repository. Các biến quan trọng:

| Biến | Vai trò |
| --- | --- |
| `SECRET_KEY` | JWT secret, tối thiểu 32 ký tự |
| `DATABASE_URL` | SQLite hoặc PostgreSQL URL |
| `GEMINI_API_KEY` | Gemini backend key |
| `IMAGE_PROVIDER` | `gemini` hoặc `openai` |
| `OPENAI_API_KEY` | OpenAI image key khi chọn provider OpenAI |
| `ALLOWED_ORIGINS` | CORS origins |
| `UPLOAD_DIR` | Thư mục lưu file |
| `VITE_API_URL` | Backend URL của frontend |
| `SMTP_*` | Email verification/password reset |
| `FFMPEG_BINARY` / `FFPROBE_BINARY` | Binary xử lý video |

## 9. Kiểm thử và bằng chứng hiện có

Các kết quả đã xác minh gần nhất:

- Backend targeted regression Plan 09: **74 passed**, 1 warning deprecation
  từ Starlette/httpx.
- Schema manifest/state/bootstrap tests: PASS.
- Explicit SQLite bootstrap: PASS tại `20261001_0016`.
- FastAPI startup trên database mới: PASS.
- `GET /health`: HTTP 200.
- Demo login qua API: HTTP 200 và token được cấp; token không in vào log.
- TTS focused tests: PASS; real Edge TTS ngắn đã từng thành công.
- Frontend `npm run build`: PASS.
- Python compile check: PASS.
- Frontend user message alignment: đã sửa và build PASS.

Các kết quả trên không đồng nghĩa với:

- PostgreSQL concurrency/runtime đã PASS.
- Alembic historical chain từ database rỗng đã PASS.
- Real Gemini image/video quota/provider đã PASS.
- FFmpeg/FFprobe container rendering đã PASS.

## 10. Tài khoản demo local

Database local mới có tài khoản demo:

```text
username: AdGenAI
email:    adgenai@example.com
```

Password không được ghi trong tài liệu hoặc commit. Nếu đổi database hoặc tạo lại
database, cần đăng ký lại tài khoản demo.

## 11. Vấn đề còn mở và hướng tiếp theo

1. Xác minh PostgreSQL disposable cho schema validator, concurrency và migration.
2. Chọn chiến lược repair legacy cho `chatbot.db` hoặc database triển khai có dữ liệu.
3. Không sửa revision `0001–0016` khi chưa có bằng chứng về lịch sử phát hành.
4. Xác minh real FFmpeg/FFprobe trong container cho video editing.
5. Xác minh real Gemini image/video provider với quota/access phù hợp; không retry
   request có thể phát sinh chi phí nếu chưa có idempotency rõ ràng.
6. Bổ sung recovery lease/heartbeat/reconciliation cho job nếu deployment cần chịu
   crash worker lâu dài.
7. Giữ tài liệu đồng bộ sau mọi thay đổi API, schema, provider hoặc deployment.

## 12. Nguồn sự thật trong code

- App startup: `backend/app/main.py`
- Cấu hình: `backend/app/core/config.py`, `backend/.env.example`
- Database guard: `backend/app/database/database.py`
- Schema state/validator/manifest: `backend/app/database/`
- Auth: `backend/app/api/auth.py`, `backend/app/services/auth_service.py`
- Chat: `backend/app/api/message.py`, `backend/app/services/`
- Media API: `backend/app/api/media.py`, `backend/app/services/media/`
- Voiceover: `backend/app/api/voiceover.py`, `backend/app/services/voiceover/`
- Frontend chat bubble: `frontend/src/components/chat/MessageBubble/`
- Frontend API clients: `frontend/src/services/api/`
- Tests: `backend/tests/`, `frontend/tests/`
- Deployment: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`,
  `render.yaml`
