# Plan 09 — Checkpoint 6: Runtime Readiness & Real Media Verification

Ngày: 2026-10-01

## Lệnh đã chạy và kết quả

Từ workspace root:

```powershell
Get-Command docker,docker-compose,ffmpeg,ffprobe
```

Kết quả thực tế:

```text
docker=NOT_FOUND
docker-compose=NOT_FOUND
ffmpeg=NOT_FOUND
ffprobe=NOT_FOUND
```

Do Docker CLI không tồn tại, các lệnh `docker version`, `docker compose version` và `docker info` được skip; không có bằng chứng Docker daemon đang chạy.

Không chạy `docker compose build`, `docker compose up`, `docker compose exec` hoặc real FFmpeg smoke test vì runtime prerequisite không tồn tại.

## Dockerfile và Compose audit

`backend/Dockerfile` có:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg
```

Package `ffmpeg` trong Debian image cung cấp cả `ffmpeg` và `ffprobe`, nhưng binary/container chưa được chạy thực tế ở máy này.

Backend chạy bằng user system `adgen`; Compose mount:

```text
UPLOAD_DIR=/app/uploads
upload_data:/app/uploads
```

Do đó cấu hình đã chuẩn bị cho media storage persistent và binary runtime trong container. Quyền đọc/ghi `/app/uploads` chưa thể xác minh vì container chưa khởi động.

## Provider configuration audit

Lệnh đã chạy trong backend:

```powershell
python -c "from app.core.config import settings; from app.services.media.providers.factory import build_video_generation_provider; p=build_video_generation_provider(); print('provider=',p.provider_id); print('model=',settings.GEMINI_VIDEO_MODEL); print('sdk-configured=',bool(settings.GEMINI_API_KEY)); print('ffmpeg_binary=',settings.FFMPEG_BINARY); print('ffprobe_binary=',settings.FFPROBE_BINARY); print('upload_dir=',settings.UPLOAD_DIR)"
```

Kết quả:

```text
provider= gemini-veo
model= veo-3.1-generate-preview
sdk-configured= True
ffmpeg_binary= ffmpeg
ffprobe_binary= ffprobe
upload_dir= ...\backend\uploads
```

API key chỉ được kiểm tra bằng boolean, không in giá trị. Không gọi Gemini và không retry provider. Real smoke test trước đó đã bị `429 RESOURCE_EXHAUSTED`; quota/access vẫn là blocker chưa được thay đổi.

## Phase 2/4 real FFmpeg

Chưa thực hiện các bước upload, trim, aspect/crop, text/CTA, subtitle, download và ffprobe vì không có Docker hoặc FFmpeg runtime.

Các kết quả mock/fake trước đó vẫn chỉ là contract/state tests, không phải real rendering evidence. Không tạo output giả và không đánh dấu source/version runtime thành công.

## Phase 3 real Veo

Chỉ thực hiện preflight cấu hình không gọi provider thật. Điều kiện để chạy lại một smoke test duy nhất:

1. Docker Desktop/daemon hoạt động hoặc backend runtime tương đương có FFmpeg/FFprobe.
2. Gemini project có quyền truy cập model `veo-3.1-generate-preview`.
3. Quota/billing được xác nhận đủ; không còn blocker `429 RESOURCE_EXHAUSTED`.
4. Chạy một request prompt ngắn, poll đến completed/failed, download nhiều nhất một lần nếu completed.
5. Probe output, kiểm tra `MediaAsset`, `MediaJob`, preview/download và không retry tự động.

Không đổi API key, project, model hoặc billing trong checkpoint này.

## Code/test changes

Không sửa source code, dependency, migration, Dockerfile, Compose hoặc hệ điều hành.

Các test mock/unit trước đó vẫn được giữ nguyên; checkpoint này chỉ xác minh điều kiện runtime. Không có real media test nào PASS.

## Kết luận

`PHASE 2 REAL RENDERING = BLOCKED`

Blocker trực tiếp: thiếu Docker CLI/Compose và FFmpeg/FFprobe local. Bước thủ công cần người dùng thực hiện: cài và khởi động Docker Desktop, sau đó chạy các lệnh trong `docs/11-environment-test-plan.md`.

`PHASE 3 REAL PROVIDER = BLOCKED`

Blocker: chưa xác nhận quota/access sau lỗi `429 RESOURCE_EXHAUSTED`; không gọi lại Gemini trong checkpoint này.

`PLAN 09 = IN PROGRESS`
