# Plan 09 — Checkpoint 5: Versioning và Partial Execution Recovery

Ngày: 2026-10-01

## Phạm vi

Đã đối chiếu `docs/09-ke-hoach-tao-anh-video.md` và trace model, Image/Video service, conversational API, Media Studio và test hiện tại. Không gọi Gemini thật, không cài Docker/FFmpeg, không thêm dependency, migration, worker hoặc queue.

## A. Versioning

### Nguyên nhân gốc

Image và Video trước đây đều cấp số bằng `source.version_number + 1`. Với cây:

```text
original v1 → edit v2
reopen original v1 → edit khác v2
```

hai asset khác nhau có thể cùng `version_number=2`. `parent_asset_id` vẫn đúng nhưng số version không nhất quán khi branch từ version cũ.

### Cách sửa

Thêm `backend/app/services/media/versioning.py` với `next_media_version_number()`:

- tìm root bằng cách đi ngược `parent_asset_id` trong cùng user/conversation/kind;
- lấy toàn bộ descendants của root;
- cấp `max(version_number) + 1` trong lineage đó;
- vẫn giữ `parent_asset_id` trỏ đúng source;
- không ghi đè file hoặc asset cũ.

Image `MediaService` và mọi đường tạo edit của `VideoService` dùng chung helper này. Upload mới vẫn bắt đầu từ version 1. Sau audit concurrency, schema đã bổ sung `root_asset_id` và unique constraint `uq_media_assets_lineage_version` qua migration `20261001_0015`; migration dừng nếu dữ liệu legacy không thể backfill an toàn.

### Regression đã thêm

- Image: edit original tạo v2, edit lại original tạo v3; cả hai parent đều là original và file vẫn tồn tại.
- Video: cùng kịch bản; cả hai output vẫn download được và source không bị thay đổi.
- Chuỗi tuyến tính hiện có `v1 → v2 → v3` vẫn giữ nguyên.

### Rủi ro còn lại

Helper kết hợp unique constraint và bounded retry để xử lý version conflict. SQLite collision test đã pass; PostgreSQL concurrent runtime chưa được xác minh.

## B. Partial Execution Recovery

### Backend contract

`ConversationalEditExecutionResponse` hiện hỗ trợ:

- `completed`: toàn bộ operation thành công;
- `partial`: operation thất bại sau khi đã tạo ít nhất một asset completed;
- `failed`: operation đầu tiên thất bại, chưa có asset completed.

Response có thêm:

- `created_assets`: chỉ các asset đã tạo thành công trước lỗi;
- `output_asset`: asset completed cuối cùng nếu có;
- `failed_operation_index`;
- `failed_operation` trong allowlist;
- `error` là thông báo an toàn cho client.

`VideoEditPlanService.execute_plan()` vẫn gọi `validate_plan()` toàn bộ trước operation đầu tiên. Khi processor/service fail trong vòng lặp, service ném `ConversationalEditExecutionError` kèm prefix assets đã hoàn thành. API trả outcome có cấu trúc thay vì báo completed hoặc làm mất danh sách prefix.

Asset gốc và prefix assets không bị rollback hoặc xóa. Asset operation đang fail vẫn được VideoService đánh dấu `failed` và output tạm được cleanup theo flow hiện tại. Không có retry tự động và không tạo worker/queue mới.

### Frontend recovery

Media Studio dùng `getConversationalExecutionOutcome()` để:

- chỉ báo success khi `status=completed`;
- hiển thị partial failure hoặc complete failure bằng thông báo an toàn;
- chọn `latestAssetId` làm source tiếp theo khi có prefix completed;
- reload media library để preview/download các asset còn nguyên;
- bỏ plan execution sau khi có outcome, không tự chạy lại plan.

Media library hiện có sẵn preview và download cho completed assets, nên prefix asset vẫn có thể mở/chọn/tải xuống sau partial failure.

## Test bắt buộc và kết quả

### Backend targeted

Lệnh:

```text
cd backend
python -m compileall -q app tests
python -m unittest tests.test_media_api tests.test_video_edit_api tests.test_conversational_video_edit
```

Kết quả:

```text
compileall: PASS
72 tests: PASS
```

Đã bao phủ:

- edit version cũ sau khi đã có version mới;
- chuỗi nhiều operation thành công;
- operation đầu tiên thất bại → `failed`, không có `created_assets`;
- operation giữa chuỗi thất bại → `partial`, prefix asset được trả về;
- ownership/conversation scope hiện có vẫn pass;
- original và partial assets tồn tại, không overwrite;
- download partial asset;
- preflight invalid plan không tạo operation đầu tiên.

### Frontend

Lệnh:

```text
cd frontend
npm test
npm run build
```

Kết quả:

```text
30 tests: PASS
production build: PASS
```

Frontend tests mới kiểm tra partial outcome chọn đúng asset cuối cùng và complete failure không tự chọn output giả.

### Full backend regression

```text
python -m unittest discover -s tests -p 'test*.py'
```

Kết quả: **195 tests, 2 failures, 3 errors**.

Hai failure:

- `test_brands.BrandApiTest.test_brand_context_reaches_ai_and_is_snapshotted` — `ADGEN_STREAM_ERROR`;
- `test_templates.TemplateApiTest.test_list_search_filter_and_favorites_are_user_scoped` — fixture có 7 template thay vì tối thiểu 10.

Ba error:

- `test_conversation_management...test_ad_brief_is_validated_stored_and_sent_to_ai_history` — `KeyError: prompt_type`;
- `test_extraction_suite` — thiếu `edge_tts`;
- `test_voiceover_flow` — thiếu `edge_tts`.

Hai failure và ba error này đã có trước checkpoint 5 (baseline 189 tests với cùng 2F/3E; số test hiện tăng do regression tests mới), nên không có bằng chứng do focused fix gây ra.

## Files thay đổi

- `backend/app/services/media/versioning.py` — helper cấp số theo lineage.
- `backend/app/services/media/media_service.py` — Image dùng helper.
- `backend/app/services/media/video_service.py` — mọi Video edit dùng helper.
- `backend/app/schemas/media.py` — response completed/partial/failed.
- `backend/app/services/media/video_edit_plan_service.py` — exception mang prefix assets và failed operation.
- `backend/app/api/media.py` — structured partial/failed response, safe error, HTTP outcome không giả success.
- `backend/tests/test_media_api.py` — Image branch version regression.
- `backend/tests/test_video_edit_api.py` — Video branch version và failure injection.
- `backend/tests/test_conversational_video_edit.py` — first/mid operation failure recovery.
- `frontend/src/utils/conversationalEdit.js` — outcome mapping.
- `frontend/src/components/chat/MediaStudio/MediaStudio.jsx` — partial/failed UX và chọn output recoverable.
- `frontend/tests/conversationalEdit.test.js` — frontend recovery regression.
- `docs/13-versioning-partial-recovery.md` — báo cáo này.

Checkpoint 5 không thêm dependency, worker hoặc queue. Migration `20261001_0015` cho root lineage và unique constraint, cùng migration `20261001_0016` cho idempotency, được bổ sung ở các checkpoint sau. Không sửa Chat, Voice Studio hay provider.

## Kết luận

`VERSIONING = PARTIAL`

Branch versioning tuần tự đã được sửa và test PASS cho Image/Video; unique lineage constraint và bounded retry đã được thêm. PostgreSQL concurrent runtime vẫn chưa được xác minh.

`PARTIAL EXECUTION RECOVERY = PASS`

API không báo completed giả, trả prefix assets và failure metadata; frontend hiển thị outcome, giữ source/partial assets và không tự retry.

`REAL RUNTIME = STILL BLOCKED`

Các test dùng fake processor. Chưa xác minh FFmpeg/ffprobe thật; Gemini vẫn không được gọi.

`PLAN 09 = IN PROGRESS`

## C. Cập nhật sau Checkpoint 9I-B/C và 9J

- Conversational edit có `MediaEditRequest` và migration `20261001_0016` để lưu idempotency key, payload hash, status, created asset IDs và failure information.
- Cùng key/cùng payload replay kết quả; cùng key/khác payload trả `409`; request `processing` không chạy processor lần hai; partial result được giữ lại.
- Frontend tạo và giữ idempotency key trong cùng lần thực thi, không tự động retry mù.
- Targeted backend media/video/versioning/idempotency: `141/141 PASS`; frontend: `35/35 PASS`; production build: PASS.
- Chưa tuyên bố exactly-once trên PostgreSQL hoặc sau crash vì chưa có concurrent PostgreSQL test và reconciliation runtime.
- Full Alembic chain còn blocker cũ tại `20260727_0008`; không chạy migration trên database người dùng thật.