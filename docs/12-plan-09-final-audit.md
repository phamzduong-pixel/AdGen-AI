# Final Audit — AdGen AI Plan 09

Ngày audit: 2026-10-01

## Phạm vi và giới hạn

Audit này đối chiếu `docs/09-ke-hoach-tao-anh-video.md` với implementation, API schema, frontend, automated tests và runtime hiện có. Không gọi Gemini thật, không cài Docker/FFmpeg và không thực hiện thay đổi phá hủy.

Máy Windows hiện tại không có `docker`, `docker-compose`, `ffmpeg` hoặc `ffprobe`. Dockerfile có khai báo cài FFmpeg cho backend image, nhưng image/container chưa được chạy kiểm chứng. Vì vậy các test dùng fake/mock processor chỉ chứng minh contract và state transition, không chứng minh render video thật.

## Bảng đối chiếu

| Hạng mục | Implementation | Automated tests | Real runtime | Trạng thái |
|---|---|---|---|---|
| Phase 1 — image generate, storage, ownership, preview/download | PASS — `MediaAsset`, local storage, ownership/conversation checks, image MIME/signature/size validation và version-preserving edit đã có | PASS — media API/provider tests bao phủ generate, edit, permission, storage, failed provider và original preservation | BLOCKED — chưa có bằng chứng execution provider thật và end-to-end runtime | PARTIAL |
| Phase 2 — trim | PASS — schema, duration validation, controlled processor, output validation và version mới | PASS — API/service tests với fake processor | BLOCKED — chưa chạy FFmpeg/ffprobe thật | BLOCKED |
| Phase 2 — aspect/crop | PASS — allowlist aspect, crop processor, dimensions/output validation | PASS — API/service tests với fake processor | BLOCKED — chưa chạy FFmpeg/ffprobe thật | BLOCKED |
| Phase 2 — text overlay / CTA overlay | PASS — structured parameters, bounded timing/position/font/color và controlled FFmpeg argv | PASS — API/service tests | BLOCKED — font/rendering thực tế chưa được kiểm chứng | BLOCKED |
| Phase 2 — subtitle | PASS — structured entries, timing validation, subtitle file tạm được tạo qua controlled path; lỗi timestamp milliseconds đã được sửa | PASS — API/service và processor tests | BLOCKED — chưa kiểm chứng Unicode/font/rendering bằng FFmpeg thật | BLOCKED |
| Phase 2 — volume / mute | PASS — parameter validation, source preservation và output validation | PASS — API/service tests | BLOCKED — chưa chạy FFmpeg thật | BLOCKED |
| Phase 2 — merge | PASS — source video được kiểm tra ownership/conversation/type/status, compatibility được probe trước khi tạo output | PASS — merge/permission/error tests | BLOCKED — chưa chạy FFmpeg/ffprobe thật | BLOCKED |
| Phase 3 — Gemini Veo provider, MediaJob, submit/poll/download | PASS — provider adapter, operation ID, polling, failed/retryable mapping và output asset state đã có | PASS — provider/service/API tests bằng mock | BLOCKED — smoke test thật trước đó bị `429 RESOURCE_EXHAUSTED`, chưa có video thật | BLOCKED |
| Phase 3 — frontend polling, recovery, preview/download | PASS — trạng thái processing/completed/failed và recovery UI đã tích hợp | PASS — frontend tests và production build | BLOCKED — chưa có asset Veo thật để kiểm chứng toàn tuyến | BLOCKED |
| Phase 4 — deterministic parser và structured plan | PASS — parser không gọi shell/LLM tùy ý; operation/parameter được chuyển thành schema có allowlist | PASS — parser/helper/API tests | BLOCKED — execution cuối vẫn phụ thuộc FFmpeg thật | BLOCKED |
| Phase 4 — preflight toàn bộ plan trước execution | PASS — API preview validate plan; execute endpoint kiểm tra lại toàn plan trước vòng lặp operation | PASS — test timing operation sau và source invalid chứng minh operation đầu tiên không được tạo khi preflight fail | BLOCKED — chưa render runtime thật | BLOCKED |
| Phase 4 — operation order, merge position, lineage | PASS — merge chỉ ở index 0; mỗi source được resolve theo user/conversation; các operation sau dùng output trước đó | PASS — order, merge scope, version chain và source preservation tests | BLOCKED — chưa kiểm chứng render chuỗi thật | PARTIAL |
| Cross-cutting security/storage/error handling | PASS — auth dependency, ownership/conversation scope, MIME/signature/size checks, path traversal protection, `shell=False`, controlled argv, cleanup/error state | PASS — media/video/Phase 4 tests | PARTIAL — quyền filesystem/container và lỗi runtime thật chưa kiểm chứng | PARTIAL |
| Regression — chat, upload, Voice Studio, advertising flows | PASS về các đường code không bị sửa ngoài media scope | PARTIAL — media targeted suite pass; full backend còn baseline failures/errors bên dưới | BLOCKED/PARTIAL — chưa có môi trường production/container đầy đủ | PARTIAL |

## Audit chi tiết Phase 4 và các rủi ro quan trọng

### 1. Preflight trước operation đầu tiên

Đã xác minh trong `video_edit_plan_service.py` và `media.py`:

- parser tạo `ConversationalEditPlan` từ instruction theo allowlist;
- API preview gọi `validate_plan()`;
- API execute kiểm tra source trong plan khớp route source;
- `execute_plan()` gọi `validate_plan()` lại trước khi bắt đầu vòng lặp;
- validation kiểm tra source, loại media, ownership, conversation, duration, timing, merge sources và giới hạn operation;
- test có trường hợp operation sau bị invalid và xác nhận không tạo version đầu tiên.

Kết luận: không có bằng chứng operation đầu tiên chạy trước khi toàn bộ plan được validate.

### 2. Merge và isolation

Trong conversational plan, merge chỉ hợp lệ tại vị trí đầu tiên. Merge phải bao gồm source của route và các source ID được gửi rõ ràng; không nhận filesystem path hoặc FFmpeg command từ user. Mọi source được resolve bằng user hiện tại, conversation hiện tại, `kind=video` và trạng thái completed. Technical merge service còn probe compatibility trước khi tạo output.

Kết luận: ownership/conversation isolation và vị trí merge đã được kiểm tra ở contract/test level. Real container execution chưa được kiểm chứng.

### 3. Version number khi edit version cũ

Đã xác minh `video_service.py` đang tạo version mới theo:

```text
new_version_number = source.version_number + 1
parent_asset_id = source.id
```

Với chuỗi tuyến tính `v1 → v2 → v3`, cách này hoạt động và test hiện có chứng minh source không bị overwrite. Tuy nhiên, nếu `v1` đã có `v2`, sau đó reopen và edit lại `v1`, implementation có thể tạo thêm một asset cũng mang `version_number=2`. `parent_asset_id` vẫn phân biệt được hai nhánh, nhưng số version không unique trong cùng lineage/root.

Kết luận: source preservation và parent lineage PASS; version numbering khi branch từ version cũ là PARTIAL/WARNING.

Đề xuất focused fix tối thiểu, chưa thực hiện trong audit: xác định root lineage và cấp số tiếp theo bằng `max(version_number)` trong lineage/conversation rồi cộng một, hoặc bổ sung một định danh version/lineage duy nhất nếu product cần hiển thị branch rõ ràng. Cần cân nhắc unique constraint/migration trước khi áp dụng; không nên sửa bằng cách overwrite hoặc đổi kiến trúc trong audit này.

### 4. Lỗi giữa chuỗi operation

Nếu processor fail ở operation giữa chuỗi, service đánh dấu asset đang tạo là failed, dọn output lỗi và propagates lỗi HTTP; các version completed trước đó không bị overwrite. Frontend chỉ chuyển source sang output sau khi API trả completed, nên không có bằng chứng frontend báo completed giả.

Giới hạn còn lại: response lỗi không trả danh sách các intermediate assets đã tạo trước khi fail. Các asset này vẫn ở DB/list và source cũ vẫn dùng được, nhưng UI không nhận được partial result trực tiếp từ response lỗi. Đây là PARTIAL về khả năng recovery/hiển thị, không phải mất dữ liệu hay false success.

### 5. Output validation và security

Video service kiểm tra file tồn tại, non-empty, giới hạn size, MP4/container signature `ftyp`, metadata qua ffprobe, duration, dimensions và audio metadata trước khi completed. Local storage resolve path dưới upload root và ngăn path traversal/symlink escape. Processor dùng argv cố định với `shell=False`; user/LLM không thể truyền arbitrary FFmpeg command hoặc filesystem path.

Các assertion trên đã được kiểm tra qua code và fake/mock tests. File signature, duration, dimensions, audio track và cleanup trong FFmpeg runtime thật chưa được xác minh trên máy hiện tại.

## Phân biệt test và runtime

Các kết quả dưới đây không phải bằng chứng render/provider thật:

- Phase 2 tests dùng fake video processor hoặc mock subprocess/provider.
- Phase 3 provider tests mock Gemini operation/poll/download.
- Phase 4 tests kiểm tra parser, preflight, state, permission và version chain; không thay thế FFmpeg runtime.
- Image tests kiểm tra provider contract/storage/DB bằng mock hoặc test fixture; chưa chứng minh một request provider thật trong môi trường hiện tại.

## Test đã chạy

Lệnh và kết quả:

```text
python -m unittest tests.test_conversational_video_edit tests.test_video_edit_api tests.test_media_api tests.test_media_generation tests.test_video_generation tests.test_gemini_video_provider tests.test_video_processor
90 tests, OK

python -m unittest discover -s tests -p 'test*.py'
189 tests, 2 failures, 3 errors

python -m compileall -q app tests
PASS

frontend: npm test
28 tests, 28 pass

frontend: npm run build
PASS
```

Targeted count 90 bị tăng do `test_conversational_video_edit.py` kế thừa test class video API hiện có; đây là duplicate test collection, không được diễn giải thành 90 test case hoàn toàn độc lập.

Full backend failures/errors:

1. `test_brands.BrandApiTest.test_brand_context_reaches_ai_and_is_snapshotted` — FAIL, nhận `ADGEN_STREAM_ERROR` thay vì nội dung kỳ vọng.
2. `test_templates.TemplateApiTest.test_list_search_filter_and_favorites_are_user_scoped` — FAIL, fixture chỉ có 7 template thay vì điều kiện test yêu cầu ít nhất 10.
3. `test_conversation_management.ConversationManagementApiTest.test_ad_brief_is_validated_stored_and_sent_to_ai_history` — ERROR, `KeyError: prompt_type`.
4. Import `test_extraction_suite` — ERROR vì môi trường thiếu dependency `edge_tts`.
5. Import `test_voiceover_flow` — ERROR vì môi trường thiếu dependency `edge_tts`.

Hai failure và ba error này đã xuất hiện ở full backend run trước Phase 4 (khi tổng số test là 147), nên được phân loại là baseline/environment issues; không có bằng chứng chúng do Phase 4 gây ra. Không sửa trong audit này.

## Files

Audit này chỉ tạo file báo cáo:

- `docs/12-plan-09-final-audit.md`

Các file implementation được đối chiếu gồm `backend/app/services/media/media_service.py`, `backend/app/services/media/video_service.py`, `backend/app/services/media/video_processor.py`, `backend/app/services/media/video_edit_plan_service.py`, `backend/app/services/media/video_generation_service.py`, `backend/app/services/media/providers/gemini_video_provider.py`, `backend/app/api/media.py`, `backend/app/schemas/media.py`, Media Studio/media API frontend và các test media/video/Phase 4. Không có source code, dependency, migration hoặc cấu hình runtime nào được sửa trong audit này.

## Kết luận

`PLAN 09 IMPLEMENTATION = PARTIAL`

Các contract Phase 1–4, permission, preflight, allowlist, version parent và frontend flow đã có automated evidence. Tuy nhiên Plan 09 chưa thể gọi là hoàn tất vì Phase 2 chưa có real FFmpeg/ffprobe rendering và Phase 3 chưa có real Gemini video generation/download/validation thành công. Ngoài ra version number khi tạo branch từ version cũ và partial result response của conversational chain vẫn là các warning cần focused decision.

`PHASE 2 REAL RENDERING = BLOCKED`

Local Windows thiếu Docker/FFmpeg/FFprobe; Dockerfile có cài FFmpeg nhưng chưa chạy container để xác minh.

`PHASE 3 REAL PROVIDER = BLOCKED`

Real smoke test trước đó nhận `HTTP 429 RESOURCE_EXHAUSTED`; chưa có video thật để xác minh submit, polling, download và completed asset.

`REGRESSION STATUS = PARTIAL`

Media/video targeted tests, frontend tests, build và compile pass. Full backend vẫn có 2 baseline failures và 3 baseline/environment errors như trên; Voice Studio full import chưa chạy được vì `edge_tts` thiếu.

`REMAINING BLOCKERS =`

1. Cần Docker runtime có FFmpeg/FFprobe để verify upload → edit → probe → download thật cho Phase 2 và execution chuỗi Phase 4.
2. Cần quota/access/billing hợp lệ cho Gemini Veo và một smoke test duy nhất để xác minh Phase 3 real provider; không retry liên tục.
3. Cần quyết định focused fix cho version numbering khi edit branch từ version cũ.
4. Nên bổ sung cơ chế trả/hiển thị partial created assets khi operation giữa chuỗi thất bại.
5. Cần xử lý hoặc ghi nhận riêng baseline backend failures và môi trường thiếu `edge_tts` trước khi kết luận regression toàn hệ thống.

Do các blocker runtime còn tồn tại, **không đặt `PLAN 09 COMPLETE`**.

## Cập nhật section 02/10/2026

Các hạng mục đã hoàn thành sau audit:

- Đã vô hiệu hóa đường legacy auto-repair còn sót trong `backend/app/database/database.py`; runtime không còn đường private nào được phép âm thầm chạy DDL/DML.
- Đã bổ sung bootstrap explicit và legacy reconciliation inspect-only trong `backend/app/database/bootstrap.py` và `backend/app/database/legacy_reconciliation.py`.
- Đã tạo database local mới `backend/adgen_dev.db`, kiểm tra schema `PASS` tại revision `20261001_0016` và xác minh FastAPI startup qua `/health` trả HTTP 200.
- Database cũ `chatbot.db` không bị xóa hoặc sửa; nó vẫn được phân loại `MANAGED_SCHEMA_MISMATCH` và cần quy trình repair riêng nếu muốn bảo toàn dữ liệu.
- Regression schema/Plan 09 đã đạt 74 tests passed, 1 warning deprecation từ Starlette/httpx; frontend build đạt PASS.
- Tài khoản demo local đã được tạo trong database mới bằng password hash; mật khẩu không được ghi vào tài liệu.
- Tin nhắn user trên frontend đã được chỉnh `text-align: left` trong `MessageBubble.css`, không ảnh hưởng cách hiển thị message assistant.

Trạng thái nghiệm thu vẫn là **PARTIAL** ở cấp toàn Plan 09 vì PostgreSQL disposable,
real FFmpeg/FFprobe và real Gemini provider chưa được xác minh đầy đủ; explicit
SQLite bootstrap và các đường code/test local đã ổn định trong phạm vi đã kiểm tra.
