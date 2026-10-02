# Environment Test Plan — Phase 2/Phase 3

## Trạng thái hiện tại

```text
PHASE 2 REAL RENDERING = BLOCKED
PHASE 3 REAL PROVIDER = BLOCKED
PLAN 09 = IN PROGRESS
```

Các trạng thái trên chỉ thay đổi sau khi có bằng chứng runtime thật. Unit test, mock provider và fake processor không được dùng để tuyên bố real rendering hoặc real Veo generation thành công.

## 1. Điều kiện môi trường

Checklist chạy trên Windows PowerShell:

```powershell
docker version
docker compose version
```

Cần có Docker Desktop đang chạy. Không cài Docker hoặc thay đổi PATH tự động trong phạm vi dự án.

Kiểm tra file cấu hình mà không in secret:

```powershell
Get-Content .env | Select-String '^(GEMINI_API_KEY|POSTGRES_PASSWORD|SECRET_KEY)=' | ForEach-Object { $_.Line.Split('=')[0] + '=CONFIGURED' }
```

Không copy hoặc ghi API key, password hay secret vào tài liệu, log hoặc issue.

## 2. Phase 2 — real FFmpeg smoke test

### Khởi động runtime

Từ workspace root:

```powershell
docker compose build backend
docker compose up -d db backend frontend
docker compose ps
```

Chờ backend đạt healthcheck:

```powershell
docker compose ps backend
Invoke-WebRequest http://localhost:8000/health
```

### Xác nhận binary và quyền storage

```powershell
docker compose exec backend ffmpeg -version
docker compose exec backend ffprobe -version
docker compose exec backend sh -lc 'id && test -r /app/uploads && test -w /app/uploads && mkdir -p /app/uploads/.runtime-check && touch /app/uploads/.runtime-check/probe && rm /app/uploads/.runtime-check/probe && rmdir /app/uploads/.runtime-check && echo upload-read-write=PASS'
```

Kết quả cần có:

- `ffmpeg` chạy trong backend container;
- `ffprobe` chạy trong backend container;
- user runtime đọc/ghi được `/app/uploads`;
- volume upload không bị ghi vào filesystem tạm của container.

### Video test

Dùng một video test ngắn, không chứa dữ liệu người dùng. Không cần tạo video bằng FFmpeg trên Windows; có thể dùng fixture MP4 nhỏ đã được kiểm soát.

1. Đăng nhập frontend tại `http://localhost:5173`.
2. Mở hoặc tạo một conversation test.
3. Mở Media Studio và upload video test.
4. Ghi lại asset/source version ban đầu.
5. Thực hiện `trim`, ví dụ `start=0`, `end=2`.
6. Xác nhận output là asset/version mới.
7. Thực hiện thêm một operation `aspect_crop`, `text_overlay` hoặc `subtitle`.
8. Download output từ Media Studio.

Probe file output trong container bằng đường dẫn asset thực tế:

```powershell
docker compose exec backend ffprobe -v error -show_entries format=duration,format_name -show_entries stream=codec_type,codec_name,width,height -of json /app/uploads/<output-file>.mp4
```

Tiêu chí PASS:

- output tồn tại và là MP4 hợp lệ;
- FFprobe đọc được duration, dimensions và streams;
- output đúng operation đã chọn;
- source asset vẫn download được;
- source file không bị overwrite;
- version chain giữ đúng original → version mới.

Nếu bất kỳ bước container/binary nào không chạy được, dừng test và ghi:

```text
PHASE 2 REAL RENDERING = BLOCKED
```

Không thay bằng fake processor.

## 3. Phase 3 — one-time real Veo smoke test

Chỉ chạy sau khi quota/access Gemini đã được xác nhận và chỉ chạy một request có kiểm soát. Không retry tự động.

### Preflight

```powershell
docker compose exec backend python -c "from app.core.config import settings; from app.services.media.providers.factory import build_video_generation_provider; p=build_video_generation_provider(); print('provider=',p.provider_id); print('model=',settings.GEMINI_VIDEO_MODEL); print('sdk-configured=',bool(settings.GEMINI_API_KEY)); print('duration=',settings.MAX_VIDEO_GENERATION_DURATION_SECONDS)"
```

Không in giá trị API key.

### Smoke flow

1. Tạo một prompt ngắn, không nhạy cảm.
2. Gửi một request tạo video với model đã cấu hình `veo-3.1-generate-preview`.
3. Ghi lại `MediaJob.id` và provider operation ID nếu submit thành công.
4. Poll operation/job đến `completed` hoặc `failed`.
5. Nếu completed, download video đúng một lần.
6. Probe output bằng FFprobe.
7. Kiểm tra:
   - file tồn tại, non-empty, MP4 hợp lệ;
   - output duration/dimensions hợp lệ;
   - `MediaAsset.status=completed`;
   - `MediaJob.status=completed`;
   - `MediaJob.output_asset_id` trỏ tới asset đúng;
   - preview và download hoạt động trên Media Studio.

Nếu submit trả `429 RESOURCE_EXHAUSTED`, không retry. Ghi nhận quota/access blocker và giữ:

```text
PHASE 3 REAL PROVIDER = BLOCKED
```

Không đổi API key, Google project, model hoặc billing trong test này.

## 4. Regression trước và sau runtime test

Chạy từ workspace root/backend/frontend tương ứng:

```powershell
python -m unittest tests.test_video_generation tests.test_gemini_video_provider tests.test_media_generation tests.test_media_api tests.test_video_edit_api
python -m compileall -q app tests
```

```powershell
cd ..\frontend
npm test
npm run build
```

Kết quả mock/unit test phải được báo riêng với real runtime result.

## 5. Tiêu chí kết luận

Chỉ kết luận:

```text
PHASE 2 REAL RENDERING = VERIFIED
```

khi video thật đã được FFmpeg/FFprobe trong runtime xử lý, download và xác minh source preservation thành công.

Chỉ kết luận:

```text
PHASE 3 REAL PROVIDER = VERIFIED
```

khi Veo thật đã submit thành công, polling hoàn tất, video tải xuống được, validation pass và MediaAsset/MediaJob/frontend đều completed đúng.

Trong mọi trường hợp chưa có bằng chứng đó:

```text
PLAN 09 = IN PROGRESS
```
