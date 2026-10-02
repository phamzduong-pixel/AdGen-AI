# Tiến độ Media MVP

Ngày cập nhật: 02/10/2026

Tài liệu này ghi nhận phần đã triển khai từ kế hoạch `09-ke-hoach-tao-anh-video.md`.

## Đã hoàn thành

- Thêm `MediaAsset` với trạng thái xử lý, provider/model, metadata và liên kết version cha/con.
- Thêm provider interface cho tạo ảnh, adapter Gemini native image generation và mock provider cho test offline.
- Thêm API xác thực để tạo ảnh, chỉnh sửa ảnh bằng ảnh upload hoặc asset cũ, liệt kê asset theo conversation và tải kết quả.
- Giữ file gốc; mỗi lần chỉnh sửa tạo asset mới, không ghi đè file cũ.
- Thêm Media Studio vào header chat: prompt, tỷ lệ ảnh, ảnh tham chiếu, thư viện asset, tải xuống và tạo version chỉnh sửa tiếp theo.
- Thêm migration `20260727_0012_media_assets` và test provider/schema.

## Cấu hình

Provider mặc định là Gemini, dùng `GEMINI_API_KEY` hiện có. Có thể đổi model bằng:

```env
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
```

## Bước tiếp theo

1. Xác minh real FFmpeg/FFprobe trong Docker theo `docs/11-environment-test-plan.md`.
2. Xác minh một real Gemini Veo smoke test duy nhất sau khi quota/access được khắc phục.
3. Chạy PostgreSQL integration test cho version allocation và idempotency concurrency.
4. Hoàn tất audit migration chain cũ trước khi triển khai migration media trên môi trường thật.
5. Bổ sung component integration harness cho Media Studio recovery nếu cần chứng cứ frontend end-to-end.

Implementation media hiện đã vượt phạm vi Image MVP ban đầu và bao gồm Technical Video Editing, AI Video Generation foundation và Conversational Video Editing. Các hạng mục trên là verification/readiness, không phải mở rộng tính năng mới.