# AdGen AI — Báo cáo tổng hợp hệ thống

> Cập nhật: 09/10/2026
> Phạm vi: source code và kết quả kiểm thử hiện có trong repository  
> Trạng thái tổng thể: **Voice Studio đã có foundation cho text/file STT-TTS và reference-voice local; runtime provider thật vẫn cần xác minh riêng**. Alembic source head hiện tại: `20261006_0025`.

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
                         ├─ Local STT provider (Vosk / Google fail-closed)
                         ├─ VieNeu-TTS local reference-voice worker (optional)
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
| TTS | `edge-tts`, VieNeu-TTS reference-voice worker, mock provider | `backend/app/services/voiceover/` |
| STT | Vosk local adapter, Google Cloud adapter fail-closed | `backend/app/services/stt/`, `backend/app/api/stt.py`, `backend/app/api/video_stt.py` |
| Voice conversion | Contract foundation, provider mặc định `disabled` | `backend/app/services/voice_conversion/`, `backend/app/api/voice_conversion.py` |
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
- `backend/app/services/`: nghiệp vụ, AI, media, auth, storage, voiceover, STT, video-to-STT, voice studio và voice conversion.
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

- Trích xuất và làm sạch script thoại deterministic.
- Ưu tiên parser theo marker `VO`, `Lời thoại`, `Narration`, `Voiceover`, `MC`, `Host` và có fallback heuristic có kiểm soát cho kịch bản thoại tự nhiên không có marker; không rewrite hoặc tự thêm lời thoại.
- Giữ riêng văn bản gốc và văn bản đã lọc; người dùng có thể chuyển qua lại, chỉnh sửa và xác nhận nội dung trước khi tạo audio.
- Có hai **Content Source**: `Văn bản quảng cáo` và `File giọng nói`. File audio/video được preview, thay/xóa và định tuyến theo loại media.
- Nút **Nhận dạng lời thoại** chỉ gọi STT và điền transcript; nút tạo giọng đọc mới thực hiện TTS từ nội dung đã xác nhận. Khi transcript/provider lỗi, hệ thống không tạo transcript hoặc audio giả.
- Audio content dùng `POST /stt/transcribe`; video content dùng `POST /stt/transcribe-video`. Backend validate kích thước, MIME/signature, container/codec, duration, audio stream, FFmpeg/FFprobe, timeout và cleanup trước/sau xử lý theo contract hiện có.
- STT factory hỗ trợ provider `vosk` local khi package/model path hợp lệ; thiếu cấu hình, package hoặc model thì trả `UnavailableSTTProvider` theo fail-closed. Google Cloud adapter vẫn không được coi là runtime đã xác minh.
- Có hai **Voice Source**: `Giọng có sẵn` qua Edge TTS và `Giọng tham chiếu của tôi` qua `POST /voiceover/generate-reference`.
- Reference voice hỗ trợ file audio và video có track âm thanh; backend kiểm tra extension/MIME/signature, size/duration/codec, dùng FFmpeg trích xuất PCM mono 16 kHz và cleanup file tham chiếu/tạm. Audio kết quả được kiểm tra trước khi trả playback/download.
- VieNeu-TTS được gọi qua worker CPU/ONNX ở môi trường riêng ngoài `backend/venv`; provider chỉ hoạt động khi Python worker, model cache và các asset cần thiết sẵn sàng. Đây là reference-voice TTS, không phải Direct Voice Conversion.
- Direct Voice Conversion có các endpoint Seed-VC cho audio/video, preset/custom reference và video remux. Nhánh này chỉ chạy khi `VC_PROVIDER=seed-vc` cùng runtime ngoài repository được cấu hình; nếu thiếu sẽ fail-closed và không tự động fallback sang STT/TTS.
- Frontend đã có responsive/compact layout, light/dark compatibility, loading/error state, stale-response guard, object URL cleanup và nhãn hiển thị theo thương hiệu AdGen AI.

### Trạng thái kiểm chứng Voice Studio

| Hạng mục | Trạng thái hiện tại |
| --- | --- |
| Text → Edge TTS | Có implementation; targeted/frontend checks đã đạt; real provider từng được xác minh ở checkpoint trước |
| Audio → STT → Edge TTS | Có endpoint, validation, Vosk adapter và UI flow; authenticated E2E cần xác minh theo môi trường đang chạy |
| Video → STT → Edge TTS | Có validation/extraction/endpoint và UI routing; runtime provider thật chưa được coi là PASS |
| Text + reference audio/video → VieNeu-TTS | Có endpoint/provider worker/validation foundation; phụ thuộc môi trường model riêng, chưa mặc định production-ready |
| Direct Voice Conversion | Seed-VC source/API/UI integration đã có; runtime thật chưa PASS do thiếu cấu hình môi trường/model/reference đầy đủ |

### Trend Radar và Insight-to-Campaign

- Thu thập Trend Report có evidence/provenance, source status, stale/conflict metadata và Product Trust.
- Source policy theo user hỗ trợ `trusted`/`excluded`; `verified_only` chỉ dùng evidence đạt verification contract, không dựa trên LLM confidence.
- Trend Monitor lưu query, cadence, timezone, next run và Trend Snapshot; luồng manual/due run giữ idempotency theo `run_key`.
- Alert Engine xử lý `TREND_NEW` và `TREND_SPIKE` theo lifecycle `NEW → ACTIVE → RESOLVED`; chỉ SUCCESS hợp lệ được đánh giá, EMPTY/ERROR không tạo hoặc resolve alert.
- Advertising Angle được tạo từ claim/evidence đủ điều kiện; Brief quảng cáo, Campaign và Campaign Metric Snapshot giữ provenance và ownership.
- Lịch sử Trend Report hỗ trợ xóa an toàn bằng soft-delete `deleted_at`; evidence và downstream artifacts không bị cascade-delete.

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
revision      = 20261006_0025
```

Canonical manifest hiện mô tả **34 bảng ứng dụng** và bảng điều khiển `alembic_version`; runtime chỉ khởi động khi schema vật lý, marker và migration head khớp.

Database cũ `backend/chatbot.db` được giữ nguyên. Nó có marker
`20260727_0008` nhưng schema mismatch, nên runtime guard từ chối khởi động trên
file này để bảo vệ dữ liệu. Không được tự ý stamp hoặc chạy repair trên file đó.

### Migration history cần lưu ý

Chuỗi lịch sử từ `20260727_0001` đến `20261001_0016` còn vấn đề:

- `0001` gọi `Base.metadata.create_all()` và tạo trước một phần schema thuộc các
  revision sau.
- `0008` có thể tạo trùng index `uq_content_documents_campaign_primary`.
- Các revision sau còn nguy cơ duplicate column/table/index tùy trạng thái schema.
- SQLite disposable đã tái hiện lỗi từ database rỗng tại `0008`.
- Không rewrite migration history vì chưa xác định được database nào đã dùng revision.

Các migration sau đó đã được nối tuần tự từ `20261003_0017` đến `20261006_0025`, gồm ownership audio Voice Studio, Trend Report evidence/source status, Product Trust, Monitor/Snapshot, Alert, Advertising Angle, Brief/Metric và soft-delete lịch sử Trend Report.

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
| `STT_PROVIDER` | `vosk`, `google-cloud` hoặc rỗng để fail-closed |
| `STT_DEFAULT_LANGUAGE` | Ngôn ngữ STT mặc định, hiện là `vi-VN` |
| `STT_AUDIO_MAX_SIZE` / `STT_AUDIO_MAX_DURATION_SECONDS` | Giới hạn upload audio trực tiếp |
| `STT_PROVIDER_TIMEOUT_SECONDS` | Timeout provider STT |
| `VOSK_MODEL_PATH` | Model Vosk local; nếu rỗng dùng đường dẫn mặc định ngoài repository trên Windows |
| `VC_PROVIDER` / `VC_MODEL` | Provider/model voice conversion; mặc định provider là `disabled` |
| `VC_AUDIO_MAX_SIZE_BYTES` / `VC_AUDIO_MAX_DURATION_SECONDS` | Giới hạn input voice conversion |
| `VIENEU_PYTHON` / `VIENEU_CACHE_DIR` | Python worker và cache model VieNeu-TTS riêng |
| `VIENEU_PROVIDER_TIMEOUT_SECONDS` | Timeout worker reference voice |
| `VIENEU_REFERENCE_MAX_SIZE_BYTES` / `VIENEU_REFERENCE_MAX_DURATION_SECONDS` | Giới hạn file reference voice |
| `VIENEU_OUTPUT_MAX_SIZE_BYTES` | Giới hạn audio output reference voice |
| `FFMPEG_BINARY` / `FFPROBE_BINARY` | Binary xử lý audio/video và probing |

## 9. Kiểm thử và bằng chứng hiện có

Các kết quả đã xác minh gần nhất:

- Backend targeted regression Plan 09: **74 passed**, 1 warning deprecation
  từ Starlette/httpx.
- Schema manifest/state/bootstrap tests: PASS.
- Explicit SQLite bootstrap/runtime validation: PASS; managed local database hiện ở revision `20261006_0025`.
- FastAPI startup trên database mới: PASS.
- `GET /health`: HTTP 200.
- Demo login qua API: HTTP 200 và token được cấp; token không in vào log.
- TTS focused tests: PASS; real Edge TTS ngắn đã từng thành công.
- Frontend `npm run build`: PASS.
- Plan 17 Trend Radar: Stage 1–4 đã hoàn thành; targeted/regression tests, schema validation và migration head đã được kiểm tra theo các checkpoint.
- Frontend Voice Studio/Trend Radar hiện có lint, test và production build theo các checkpoint tương ứng.
- Voice Studio targeted suites gồm `test_stt_api.py`, `test_video_to_stt.py`, `test_vosk_stt.py`, `test_vieneu_reference_api.py`, `test_voiceover_api.py`, cùng các contract test frontend cho audio/video/file input và modal.
- Frontend Voice Studio gần nhất: **68/68 tests pass**, `npm run lint` PASS và `npm run build` PASS.
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
- Voiceover: `backend/app/api/voiceover.py`, `backend/app/services/voiceover/`, `backend/app/services/voiceover/providers/vieneu_reference_provider.py`, `backend/app/services/voiceover/providers/vieneu_worker.py`
- STT/audio/video: `backend/app/api/stt.py`, `backend/app/api/video_stt.py`, `backend/app/services/stt/`, `backend/app/services/voice_studio/`
- Voice conversion foundation: `backend/app/api/voice_conversion.py`, `backend/app/services/voice_conversion/`
- Trend Radar: `backend/app/api/trend_report.py`, `backend/app/api/insight_campaign.py`, `backend/app/services/trend_report_service.py`, `backend/app/services/trend_monitor_service.py`, `backend/app/services/trend_alert_service.py`, `backend/app/services/advertising_angle_service.py`, `backend/app/services/insight_campaign_service.py`
- Trend Radar models: `backend/app/models/trend_report.py`, `trend_monitor.py`, `trend_alert.py`, `advertising_angle.py`, `advertising_brief.py`, `evidence_source_policy.py`
- Frontend chat bubble: `frontend/src/components/chat/MessageBubble/`
- Frontend API clients: `frontend/src/services/api/`
- Trend Radar UI: `frontend/src/components/chat/TrendReportPanel/`, `frontend/src/services/api/trendReportApi.js`, `frontend/src/utils/trendReport*.js`
- Tests: `backend/tests/`, `frontend/tests/`
- Deployment: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`,
  `render.yaml`

## 13. Cập nhật nhận diện giao diện và logo (04/10/2026)

Section giao diện đã được đồng bộ theo nhận diện Login/Register và source frontend hiện tại:

- Chuẩn hóa token `--brand-mark-*` trong `frontend/src/styles/variables.css` cho mọi logo thương hiệu.
- Chế độ sáng dùng nền lavender `#eef2ff`, chữ/icon indigo `#4f46e5`, viền xanh nhạt và bóng nhẹ.
- Chế độ tối và system dark dùng nền indigo `#1e1b4b`, chữ/icon lavender `#a5b4fc`, viền `#312e81`.
- Áp dụng cho logo DG tại Sidebar, Login, Register, Recovery và Workspace; biểu tượng thương hiệu ở màn hình Chat cũng dùng cùng bộ màu.
- Logo tia sét trong tiêu đề cuộc trò chuyện đã được bỏ theo thiết kế mới; Header chỉ còn tên cuộc trò chuyện và trạng thái hệ thống.
- Avatar người dùng trong Profile/Sidebar vẫn là thành phần tài khoản riêng, không bị trộn với logo thương hiệu.
- Chat light/dark đã đồng bộ nền hội thoại, footer quanh ô nhập và composer; composer dark chỉ sáng hơn nhẹ để giữ phân cấp thị giác.

Các file nguồn chính: `frontend/src/styles/variables.css`, `frontend/src/pages/Login/Login.css`, `frontend/src/pages/Register/Register.css`, `frontend/src/components/auth/RecoveryLayout/RecoveryLayout.css`, `frontend/src/layouts/WorkspaceLayout/WorkspaceLayout.css`, `frontend/src/components/chat/EmptyState/EmptyState.css`, `frontend/src/components/chat/Sidebar/SidebarHeader/SidebarHeader.css`, `frontend/src/components/chat/Header/HeaderTitle/HeaderTitle.jsx`.

Bằng chứng kiểm tra section này:

- `npm run lint`: PASS.
- `npm test`: PASS, 38/38 frontend tests.
- `npm run build`: PASS, Vite production build thành công.
- `git diff --check`: PASS.

Các kết quả trên xác nhận implementation và frontend unit/build checks; chưa thay thế cho visual QA thủ công trên mọi trình duyệt/kích thước màn hình.

## 14. Kiến trúc logic hiện tại

```text
React 19 + Vite frontend
  Pages / components / hooks / API clients / Chat UI
             │ HTTP JSON, multipart upload, text stream
             ▼
FastAPI backend
  Routers → schemas → services → SQLAlchemy models
  Auth/JWT, ownership, validation, local file storage
             ├───────────────┬────────────────┐
             ▼               ▼                ▼
       SQLite/PostgreSQL  Gemini AI       Media/TTS providers
       Alembic            prompt/context  image/video/voiceover
```

Frontend quản lý giao diện, trạng thái hội thoại, form, preview, upload và gọi API. Backend đảm nhiệm xác thực, phân quyền, nghiệp vụ, gọi AI, lưu dữ liệu và streaming. AI pipeline kết hợp system prompt, prompt theo nền tảng, brief, thương hiệu, lịch sử hội thoại và file phù hợp trước khi gửi đến provider.

### 14.1. Media runtime

- `MediaAsset` lưu image/video, metadata, trạng thái, ownership, conversation và lineage (`parent_asset_id`, `root_asset_id`, `version_number`).
- Image flow hỗ trợ provider adapter, ảnh tham chiếu, preview/download và tạo asset mới khi chỉnh sửa.
- Video flow hỗ trợ upload/register, trim, aspect/crop, text/CTA overlay, subtitle, volume/mute và merge qua controlled processor.
- Media Studio hỗ trợ chọn source, cấu hình operation, preview/download và giữ bản gốc.
- Conversational Video Editing dùng structured plan, preflight, allowlist operation, partial recovery và idempotency.
- AI video generation dùng `MediaJob`, submit/poll/download và output validation; provider thật vẫn phụ thuộc quota/access.

Các test media dùng mock/fake processor hoặc SQLite không thay thế cho xác minh FFmpeg/FFprobe, provider thật và PostgreSQL concurrency.

## 15. Luồng AI và upload hiện tại

### Luồng tạo nội dung

```text
Request /messages hoặc /messages/stream
  → xác thực user/conversation và ownership
  → đọc brief, brand, platform, lịch sử và attachment
  → ghép system prompt + platform prompt + context
  → gọi Gemini non-stream hoặc stream
  → validation/sanitize theo luồng
  → lưu assistant message và trả kết quả
```

Luồng stream ưu tiên phản hồi nhanh; theo source hiện tại, validation và learning-dataset logging chưa hoàn toàn đồng nhất với non-stream.

### Nền tảng nội dung

Nền tảng tạo mới gồm Facebook, TikTok, Instagram, Shopee, Google Ads và Khác. Khi chọn Khác, người dùng nhập tên kênh từ 2 đến 80 ký tự. Giá trị này là dữ liệu đầu vào, không được ghi đè system prompt hoặc làm AI tự suy đoán quy định của kênh.

Các giá trị legacy như Landing Page, Email, SEO, Slogan, Viết lại và Tóm tắt vẫn có thể xuất hiện trong dữ liệu cũ để tương thích, nhưng không còn là lựa chọn nền tảng mới.

### Upload và multimodal

Upload hỗ trợ tài liệu DOCX/PDF/TXT, ảnh JPEG/JPG/PNG/WEBP và video MP4/MOV/WEBM. File được kiểm tra loại, kích thước và quyền sở hữu; video upload là source để tạo version chỉnh sửa mới, không ghi đè file gốc.

`backend/app/services/multimodal/` cung cấp các contract cho text, image, video, audio và task type tương ứng. Đây là scaffold/contract chung; chức năng thực tế phải được đối chiếu với media API/provider/service tương ứng.

## 16. Cấu trúc source chính

- `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/services/api/`: giao diện, trạng thái và client API.
- `backend/app/api/`: router HTTP theo domain.
- `backend/app/schemas/`, `backend/app/models/`: hợp đồng request/response và dữ liệu SQLAlchemy.
- `backend/app/services/`: nghiệp vụ, AI, media, auth, storage, voiceover, STT, video-to-STT, voice studio và voice conversion.
- `backend/app/database/`, `backend/alembic/`: database engine, schema guard và migration.
- `backend/tests/`, `frontend/tests/`: kiểm thử backend/frontend.

## 17. Trạng thái implementation và giới hạn

Các phase Image, Technical Video Editing, AI Video Generation foundation và Conversational Video Editing đã có contract, backend/frontend implementation và targeted tests. Việc gọi chúng là hoàn tất production vẫn cần bằng chứng runtime thật cho FFmpeg/FFprobe, Gemini provider, storage persistent và PostgreSQL concurrency.

Các giới hạn chính: chưa có refresh token; SQLite chỉ phù hợp local/demo một instance; upload production cần persistent disk hoặc object storage; stream chưa đồng nhất hoàn toàn với non-stream; quota/rate limit Gemini và media cần được cấu hình khi triển khai rộng.

## 18. Cập nhật Voice Studio và trạng thái Plan 18 (10/10/2026)

### Đã hoàn thành trong source

- Text → Edge TTS vẫn là luồng nền tảng, không bị thay đổi bởi các nhánh file/STT/reference voice.
- Voice Studio đã tách rõ Content Source (`Văn bản quảng cáo`, `File giọng nói`) và Voice Source (`Giọng có sẵn`, `Giọng tham chiếu của tôi`).
- File audio/video có preview, thay/xóa, routing theo media kind và state guard để response cũ không ghi đè trạng thái mới.
- Audio → STT dùng `/stt/transcribe`; video → STT dùng `/stt/transcribe-video`; transcript được review/edit trước bước Edge TTS.
- Backend có audio/video validation, FFprobe/FFmpeg probing/extraction, giới hạn size/duration, stable error mapping và cleanup temporary files theo các test liên quan.
- Vosk local đã có adapter/factory/configuration fail-closed; model được giữ ngoài Git và không tự tải trong request.
- Reference voice đã có `/voiceover/generate-reference`, hỗ trợ reference audio hoặc video có audio, chuyển về PCM mono 16 kHz và gọi VieNeu-TTS worker local CPU/ONNX khi môi trường riêng đã sẵn sàng.
- Voice Conversion đã có Seed-VC CPU adapter, preset/custom reference resolution, endpoint audio/video và video remux. Frontend gọi trực tiếp nhánh này khi người dùng chọn file nhưng để transcript trống.
- UI đã được tinh chỉnh responsive/compact, light/dark, loading/error, nút thao tác, transcript counter và nhãn thương hiệu AdGen AI. Các nhãn người dùng không còn hiển thị Gemini như tên sản phẩm.

### Phân biệt trạng thái runtime

- **Đã có implementation/test foundation:** routes, schemas, validation, cleanup, factory/provider adapters, frontend contract và regression tests.
- **Runtime còn điều kiện:** Vosk cần `STT_PROVIDER=vosk`, package/model path hợp lệ, FFmpeg/FFprobe và phiên xác thực hợp lệ; VieNeu cần Python worker, cache model/codec assets và đủ tài nguyên CPU/RAM.
- **Chưa được xác minh production:** authenticated E2E audio/video → STT → Edge TTS, VieNeu reference-voice runtime ổn định trên mọi file, Seed-VC inference thật, PostgreSQL/storage persistent.
- Không dùng mock/unit test để kết luận provider thật hoạt động; không coi reference-voice TTS là Direct Voice Conversion.

### Bằng chứng kiểm tra gần nhất

- Frontend tests: **68/68 pass**.
- `npm run lint`: **PASS**.
- `npm run build`: **PASS**.
- `git diff --check`: **PASS**; các cảnh báo LF/CRLF là cảnh báo line ending của working tree, không phải lỗi whitespace nội dung.
- Backend có targeted tests cho STT, video-to-STT, Vosk, reference voice, voice conversion và audio probe; kết quả runtime thật phải được báo cáo tách biệt với mock/unit tests.
- Full backend suite: **495 passed**, 74 subtests passed; OpenAPI 97 paths, health check, CORS local, migration head, compileall và `pip check` PASS.

### Giới hạn và bước tiếp theo

1. Xác minh một phiên authenticated runtime cho audio → Vosk STT → Edge TTS bằng file được phép sử dụng.
2. Xác minh riêng video → extraction → Vosk STT → Edge TTS với fixture hợp lệ, không gọi provider trả phí.
3. Kiểm tra VieNeu worker/model/cache trên máy triển khai sau khi đủ RAM và quyền sử dụng reference voice.
4. Cấu hình Python 3.10/checkpoint Seed-VC qua `SEED_VC_PYTHON` và `SEED_VC_DIR`, sau đó chạy authenticated E2E trên CPU trước khi công bố runtime PASS.
5. Bổ sung `backend/app/assets/ref_audios/manh_dung_ref.wav` hợp lệ; hiện chỉ xác minh có preset WAV Ngọc Huyền.
6. Tiếp tục giữ file tham chiếu và transcript tạm thời ngoài database, cleanup khi request kết thúc và không log secret/audio nhạy cảm.

Các tài liệu chi tiết liên quan: [01-chuc-nang-he-thong.md](./01-chuc-nang-he-thong.md), [07-huong-dan-su-dung-he-thong.md](./07-huong-dan-su-dung-he-thong.md) và [09-voice-studio-audio-transform-plan.md](./09-voice-studio-audio-transform-plan.md).