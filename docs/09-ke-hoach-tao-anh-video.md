# Kế hoạch phát triển tạo ảnh, tạo video và chỉnh sửa video

> Trạng thái: Implementation các phase chính đã triển khai; đang chờ runtime verification để đóng Plan 09
>
> Ngày lập: 30/09/2026
>
> Phạm vi tài liệu: Kế hoạch, implementation status và điều kiện xác minh runtime.
> **Cập nhật implementation 02/10/2026:** Phase 1–4 đã có implementation backend/frontend và targeted tests. Các kết quả mock/SQLite không được xem là bằng chứng real rendering/provider. Trạng thái Plan 09 vẫn `IN PROGRESS` do real FFmpeg/FFprobe, real Gemini Veo, PostgreSQL concurrency và full migration chain chưa được xác minh.

## 1. Mục tiêu

Mở rộng AdGen AI để người dùng có thể:

- Tạo ảnh quảng cáo từ brief hoặc yêu cầu tự nhiên.
- Tạo các biến thể ảnh theo sản phẩm, thương hiệu và nền tảng.
- Tải video lên để cắt, ghép, đổi tỷ lệ, thêm phụ đề, CTA, logo và âm thanh.
- Tạo video từ prompt hoặc từ kịch bản quảng cáo.
- Yêu cầu chỉnh sửa video bằng hội thoại tự nhiên.
- Xem preview, tải xuống và mở lại các phiên bản media đã tạo.

Nguyên tắc triển khai là giữ bản gốc, tạo version mới cho mỗi lần chỉnh sửa và không để nội dung người dùng ghi đè system prompt hoặc các quy tắc an toàn hiện có.

## 2. Hiện trạng hệ thống

AdGen AI hiện đã có một số nền tảng có thể tái sử dụng:

- `backend/app/services/multimodal/` đã khai báo các loại tác vụ text, image, video và audio.
- Multimodal scaffold đã có các loại tác vụ `TEXT_TO_IMAGE`, `TEXT_TO_VIDEO` và `VIDEO_TO_EDITED_VIDEO`.
- Upload hỗ trợ ảnh và video, bao gồm `.png`, `.jpg`, `.webp`, `.mp4`, `.mov` và `.webm`.
- Hệ thống đã có lưu file local, kiểm tra quyền sở hữu file và liên kết file với conversation/message.
- Voiceover đã sử dụng hướng provider adapter; có thể tham khảo cách tổ chức này cho media provider.
- Database đang dùng Alembic nên có thể mở rộng schema bằng migration mới.

Các phần đã có implementation:

- Image API/provider, `MediaAsset`, reference image, storage, ownership, preview/download và versioning.
- Video upload/register, controlled FFmpeg processor contract và Technical Video Editing operations.
- Gemini Veo provider adapter, `MediaJob`, submit/poll/download và output validation contract.
- Conversational parser, structured plan, preflight validation, partial recovery và idempotency cho `/conversational-edits`.
- Media Studio preview/download, source selection và execution status.

Các phần chưa xác minh hoặc chưa đầy đủ cho production:

- Real FFmpeg/FFprobe chưa chạy trong môi trường hiện tại.
- Real Gemini Veo chưa xác minh do quota/access blocker.
- PostgreSQL concurrency/idempotency chưa có integration test.
- Full Alembic chain còn blocker cũ tại migration `20260727_0008`.
- `MediaVersion` và `MediaOperation` chưa là model độc lập; lineage/operation hiện nằm trong `MediaAsset`.


- API/provider thực thi tạo ảnh.
- API/provider thực thi tạo video.
- Pipeline chỉnh sửa video thực tế.
- FFmpeg hoặc bộ xử lý video trong dependency/runtime.
- Media job bất đồng bộ, worker, retry và progress.
- Model riêng cho media asset, job, operation và version.
- Giao diện preview, thư viện và quản lý phiên bản media.

> Việc `StandardMultimodalProcessor.can_handle()` hỗ trợ các task media hiện mới thể hiện contract/scaffold, không có nghĩa chức năng đã chạy hoàn chỉnh.

## 3. Kiến trúc đề xuất

### 3.1. Các thành phần chính

```text
Chat/Media UI
      |
      v
Media API
      |
      +--> Prompt/Brief Context
      +--> Media Job Service
      +--> Provider Adapter
      +--> Deterministic Video Processor (FFmpeg)
      +--> Media Validation
      +--> Asset/Version Storage
      |
      v
Media Library / Conversation History
```

### 3.2. Provider adapter

Không gọi trực tiếp một provider trong UI hoặc service nghiệp vụ. Nên tạo interface riêng cho từng nhóm:

- `ImageGenerationProvider`.
- `VideoGenerationProvider`.
- `VideoEditingProvider` nếu có nhu cầu chỉnh sửa bằng AI.

Provider cụ thể có thể thay đổi mà không làm thay đổi API và luồng hội thoại của AdGen AI. Việc chọn provider, model, giới hạn, chi phí và API key cần được chốt trước khi triển khai.

### 3.3. Chỉnh sửa video an toàn

Các thao tác kỹ thuật nên dùng FFmpeg hoặc bộ xử lý được kiểm soát:

- Cắt và ghép video.
- Đổi tỷ lệ khung hình.
- Thêm text overlay, CTA và logo.
- Thêm phụ đề.
- Điều chỉnh âm lượng hoặc chèn nhạc.
- Tạo thumbnail.

AI chỉ phân tích yêu cầu tự nhiên và chuyển thành lệnh có cấu trúc. Backend phải kiểm tra lệnh theo allowlist trước khi thực thi; không cho AI tự tạo và chạy shell command tùy ý.

Ví dụ cấu trúc trung gian:

```json
{
  "operation": "trim",
  "start": 0,
  "end": 15
}
```

### 3.4. Dữ liệu media

Implementation hiện tại dùng các model/service riêng cho media; `UploadedFile` chỉ là input upload. `MediaVersion` và `MediaOperation` chưa là model độc lập; version lineage và operation nằm trong `MediaAsset`:

- `MediaAsset`: file ảnh/video/audio và metadata.
- `MediaJob`: công việc tạo hoặc xử lý media.
- `MediaVersion`: phiên bản mới sau mỗi lần chỉnh sửa.
- `MediaOperation`: lịch sử thao tác đã thực hiện.
- `MediaProviderJob`: mã job bên ngoài provider nếu provider xử lý bất đồng bộ.

File gốc không bị ghi đè. Mỗi lần chỉnh sửa tạo một version mới, có thể quay lại version trước.

## 4. Các luồng chức năng

### 4.1. Tạo ảnh

```text
Người dùng nhập yêu cầu
        -> lấy brief/thương hiệu/nền tảng
        -> tạo media job
        -> provider tạo ảnh
        -> kiểm tra kết quả và metadata
        -> lưu asset/version
        -> preview, tải xuống hoặc lưu thư viện
```

Nội dung người dùng nhập chỉ là dữ liệu đầu vào. Nó không được ghi đè system prompt, quy tắc an toàn hoặc context hệ thống.

### 4.2. Chỉnh sửa video tải lên

```text
Upload video
      -> tạo asset gốc
      -> người dùng nhập yêu cầu chỉnh sửa
      -> AI chuyển yêu cầu thành operation có cấu trúc
      -> backend kiểm tra operation
      -> FFmpeg/provider xử lý
      -> lưu version mới
      -> cập nhật trạng thái và preview
```

### 4.3. Tạo video từ prompt

Tạo video phải chạy bất đồng bộ vì thời gian xử lý và dung lượng kết quả lớn hơn chat text:

```text
Tạo yêu cầu
   -> job: pending
   -> worker: running
   -> gọi provider
   -> tải kết quả và kiểm tra
   -> job: completed/failed
   -> lưu asset/version
```

Frontend cần hiển thị trạng thái, tiến trình nếu provider hỗ trợ, lỗi, retry và nút hủy nếu có thể.

### 4.4. Chỉnh sửa video bằng hội thoại

Ví dụ:

> Cắt 5 giây đầu, thêm CTA ở cuối và đổi sang tỷ lệ TikTok.

Luồng xử lý:

```text
Yêu cầu tự nhiên
    -> AI lập kế hoạch chỉnh sửa
    -> backend kiểm tra thao tác và thông số
    -> thực thi
    -> tạo version mới
    -> trả kết quả vào hội thoại
```

## 5. Lộ trình triển khai

### Giai đoạn 0 — Chốt thiết kế và provider

- Chọn provider tạo ảnh và video.
- Xác định môi trường chạy FFmpeg.
- Xác định local storage hoặc object storage.
- Chốt giới hạn dung lượng, thời lượng, kích thước và chi phí.
- Chốt yêu cầu kiểm duyệt media.

### Giai đoạn 1 — Tạo ảnh MVP

- API tạo ảnh.
- Lưu asset và metadata.
- Preview, tải xuống và lưu thư viện.
- Tạo biến thể theo brief và nền tảng.
- Ghi lại lịch sử trong conversation.

### Giai đoạn 2 — Chỉnh sửa video kỹ thuật

- Tích hợp FFmpeg.
- Cắt, ghép, crop và đổi tỷ lệ.
- Text overlay, CTA, logo, phụ đề và âm thanh.
- Lưu version và cho phép mở lại version cũ.

### Giai đoạn 3 — Tạo video AI

- Provider adapter và media job.
- Worker bất đồng bộ.
- Theo dõi trạng thái, retry và xử lý lỗi.
- Lưu kết quả vào media library.

### Giai đoạn 4 — Chỉnh sửa bằng hội thoại

- Chuyển yêu cầu tự nhiên thành operation an toàn.
- Xác nhận lại thao tác có rủi ro hoặc tốn chi phí.
- Hiển thị lịch sử version.
- Cho phép tiếp tục chỉnh sửa từ version trước.

Khuyến nghị bắt đầu theo thứ tự **tạo ảnh -> chỉnh sửa video kỹ thuật -> tạo video AI -> chỉnh sửa video bằng hội thoại**. Cách này giảm rủi ro kỹ thuật và giúp kiểm soát chi phí tốt hơn.

## 6. Yêu cầu giao diện dự kiến

- Khu vực chọn `Tạo ảnh` và `Tạo video` cạnh luồng chat.
- Preview media ngay trong conversation.
- Hiển thị trạng thái job: đang chờ, đang xử lý, hoàn tất, lỗi.
- Nút retry và tải xuống.
- Media library cho asset đã tạo.
- Khu vực xem version và khôi phục version cũ.
- Bộ thông số tùy chọn: tỷ lệ, thời lượng, phong cách, CTA, phụ đề.
- Cảnh báo chi phí hoặc thời gian xử lý khi cần.

## 7. An toàn và tương thích

- Giữ nguyên system prompt và các quy tắc an toàn hiện có.
- Không tự bịa giá, ưu đãi, số liệu, chứng nhận hoặc thông tin sản phẩm.
- Nội dung media do người dùng nhập chỉ là input context.
- Không cho AI chạy lệnh hệ thống tùy ý.
- Giữ file gốc và dữ liệu media cũ; không migration xóa dữ liệu.
- Các conversation cũ vẫn phải mở được kể cả khi không có media version mới.
- Phải kiểm tra quyền sở hữu trước khi đọc, sửa, tải hoặc xóa asset.
- Cần có giới hạn file, thời lượng, số job và chi phí.

## 8. Các điểm cần chốt trước khi code

1. Provider nào dùng cho tạo ảnh và tạo video?
2. Video sẽ chủ yếu được tạo từ prompt hay dựng từ clip người dùng tải lên?
3. FFmpeg chạy local, Docker hay máy chủ riêng?
4. Có cần object storage ngay từ MVP không?
5. Có cần queue/worker riêng ngay từ giai đoạn tạo ảnh không?
6. Giới hạn thời lượng và dung lượng video là bao nhiêu?
7. Cách tính và hiển thị chi phí cho người dùng?
8. Mức kiểm duyệt và giới hạn nội dung media cần áp dụng?

## 9. Tiêu chí hoàn thành MVP đầu tiên

- Người dùng gửi yêu cầu tạo ảnh và nhận được trạng thái xử lý rõ ràng.
- Ảnh kết quả được lưu, preview và tải xuống.
- Asset gắn đúng conversation và người dùng sở hữu.
- Không làm hỏng luồng chat text hiện tại.
- Có xử lý lỗi và retry cơ bản.
- Không ghi đè system prompt hoặc dữ liệu sản phẩm.
- Có test cho API, quyền truy cập, job thất bại và lưu version.

## 10. Ghi chú phiên khảo sát

Tài liệu này được lập sau khi rà soát source hiện tại. Trong phiên lập kế hoạch này không sửa code, không thêm dependency, không thay đổi schema và không thay đổi database/runtime của dự án.


## 11. Trạng thái thực tế sau implementation

| Phase | Implementation | Automated tests | Real runtime | Trạng thái |
| --- | --- | --- | --- | --- |
| Phase 1 — Image MVP | Image generate/edit, reference image, storage, ownership, preview/download, versioning | Backend targeted tests PASS | Gemini/storage runtime chưa xác minh đầy đủ | PARTIAL |
| Phase 2 — Technical Video Editing | Upload/register, trim, aspect/crop, text/CTA, subtitle, volume/mute, merge, Media Studio | Backend fake-processor tests và frontend tests PASS | Real FFmpeg/FFprobe BLOCKED | PARTIAL |
| Phase 3 — AI Video Generation | Gemini Veo adapter, MediaJob, submit/poll/download, validation, UI recovery | Backend/frontend tests PASS | Real provider BLOCKED bởi quota/access | PARTIAL |
| Phase 4 — Conversational Video Editing | Parser, structured plan, preflight, allowlist, partial recovery, idempotency | Targeted backend/frontend tests PASS | PostgreSQL concurrency và real FFmpeg chưa xác minh | PARTIAL |

### Hạng mục cross-cutting đã triển khai

- Ownership và conversation scope cho media asset.
- Source preservation và version lineage bằng `parent_asset_id`, `root_asset_id`, `version_number`.
- Unique constraint và bounded retry cho version allocation.
- File/MIME/size/duration/output metadata validation.
- Không nhận arbitrary shell command hoặc filesystem path từ user/LLM.
- Idempotency durable cho conversational edit với replay, payload conflict và partial result.

### Blocker đóng Plan 09

- Cần Docker/FFmpeg/FFprobe để xác minh Phase 2 và Phase 4 bằng output thật.
- Cần quota/access hợp lệ để xác minh Gemini Veo thật.
- Cần PostgreSQL test cho concurrency/idempotency.
- Cần xử lý migration chain cũ `20260727_0008`.
- Cần component integration harness nếu muốn tuyên bố frontend recovery đã được xác minh tự động.
