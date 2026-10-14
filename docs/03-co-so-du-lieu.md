# 4. Cơ sở dữ liệu

> Schema trong mã nguồn hiện khai báo **34 bảng ứng dụng**; migration mới nhất là `20261006_0025`. Con số này mô tả schema chuẩn, không khẳng định mọi database đang chạy đã được nâng cấp tới revision đó.

## 4.1. Database runtime

- Kết nối được chọn bằng `DATABASE_URL` qua `backend/app/core/config.py`; `backend/.env.example` chỉ là cấu hình mẫu, không cho biết database nào đang được dùng.
- SQLite local/test chuẩn hóa đường dẫn tương đối về thư mục backend và bật foreign key pragma.
- Docker Compose cấu hình PostgreSQL qua driver `postgresql+psycopg` và lưu dữ liệu trong volume `postgres_data`.
- SQLAlchemy session được cấp qua `get_db()` và đóng sau mỗi request.
- `initialize_database()` ở startup **chỉ kiểm tra** trạng thái schema: chỉ chấp nhận `MANAGED_CANONICAL_SCHEMA`, từ chối database rỗng hoặc lệch chuẩn; không tự thêm cột cho SQLite cũ. Startup có thể seed mẫu hệ thống sau khi schema hợp lệ.
- Database rỗng được chuẩn bị bằng `app.database.bootstrap`/`app.database.prepare_database` theo quy trình tường minh; database đang dùng cần được backup và nâng cấp bằng Alembic. Không dùng tên file `.db` để suy ra cấu hình đang hoạt động.

### Tìm database và mã nguồn liên quan ở đâu?

```text
AdGenAI/
├── backend/
│   ├── .env.example                         # Ví dụ DATABASE_URL; không chứa cấu hình chạy thực tế
│   ├── *.db                                 # SQLite local nếu được cấu hình; dữ liệu runtime, không phải định nghĩa schema
│   ├── alembic.ini                          # Cấu hình Alembic
│   ├── alembic/
│   │   ├── env.py                           # Kết nối metadata model với migration
│   │   └── versions/                       # 25 revision 0001–0025: lịch sử thay đổi schema
│   ├── app/
│   │   ├── main.py                         # Gọi kiểm tra database lúc khởi động
│   │   ├── core/config.py                  # Đọc và chuẩn hóa DATABASE_URL
│   │   ├── database/
│   │   │   ├── database.py                 # Engine, SessionLocal, Base, get_db, startup guard
│   │   │   ├── schema_manifest.py          # Danh mục bảng/cột/constraint chuẩn
│   │   │   ├── schema_validator.py         # So sánh schema thực với schema chuẩn
│   │   │   ├── schema_state.py             # Phân loại trạng thái và revision database
│   │   │   ├── bootstrap.py                # Tạo schema cho database thực sự rỗng, có kiểm tra
│   │   │   ├── prepare_database.py         # Chuẩn bị DB rỗng hoặc xác nhận DB chuẩn
│   │   │   └── legacy_reconciliation.py    # Báo cáo trạng thái legacy, không tự sửa
│   │   └── models/
│   │       ├── __init__.py                 # Đăng ký toàn bộ model vào Base.metadata
│   │       ├── user.py, user_settings.py, user_session.py
│   │       ├── email_verification.py, password_reset.py
│   │       ├── conversation.py, message.py, uploaded_file.py
│   │       ├── brand.py, ad_template.py, saved_content.py
│   │       ├── content_activity.py, campaign.py, content_document.py
│   │       ├── voiceover_audio.py, media_asset.py, media_job.py, media_request.py
│   │       ├── evidence_source_policy.py, trend_report.py, trend_monitor.py
│   │       └── trend_alert.py, advertising_angle.py, advertising_brief.py
│   └── tests/
│       ├── test_database_bootstrap.py       # Kiểm tra bootstrap
│       ├── test_schema_manifest.py         # Kiểm tra manifest
│       └── test_schema_state.py            # Kiểm tra phân loại trạng thái
├── docker-compose.yml                      # PostgreSQL và volume postgres_data; upload_data cho file
└── render.yaml                             # Khai báo biến DATABASE_URL khi triển khai
```

**Khi được hỏi “database ở đâu?”:** Trước hết xem `DATABASE_URL` của môi trường đang chạy mà không công khai thông tin đăng nhập. Nếu là SQLite, file `.db` nằm tại đường dẫn đã cấu hình; đường dẫn tương đối được chuẩn hóa theo thư mục backend. Nếu chạy Docker Compose, bản ghi nằm trong PostgreSQL ở volume `postgres_data`. `app/models/` mô tả cấu trúc bảng, `alembic/versions/` ghi lịch sử thay đổi và `app/database/` quản lý kết nối, kiểm tra schema. File upload/âm thanh/video nằm ngoài database; các bảng tương ứng lưu metadata và đường dẫn.

| File trong `backend/app/models/` | Vai trò và bảng tương ứng |
| --- | --- |
| `user.py`, `user_settings.py`, `user_session.py` | Tài khoản, cài đặt và phiên: `users`, `user_settings`, `user_sessions` |
| `email_verification.py`, `password_reset.py` | Xác minh email và đặt lại mật khẩu: `email_verification_tokens`, `password_reset_tokens` |
| `conversation.py`, `message.py`, `uploaded_file.py` | Hội thoại, tin nhắn và tệp đính kèm: `conversations`, `messages`, `uploaded_files` |
| `brand.py` | Hồ sơ, tài sản và kiểm tra thương hiệu: `brand_profiles`, `brand_assets`, `brand_content_checks` |
| `ad_template.py`, `saved_content.py`, `content_activity.py` | Mẫu quảng cáo, nội dung lưu và hoạt động: `ad_templates`, `template_favorites`, `saved_contents`, `content_activities` |
| `campaign.py`, `content_document.py` | Chiến dịch, liên kết nội dung và phiên bản tài liệu: `campaigns`, `campaign_contents`, `content_documents`, `content_versions` |
| `voiceover_audio.py` | Metadata file giọng đọc: `voiceover_audios` |
| `media_asset.py`, `media_job.py`, `media_request.py` | Metadata asset, tác vụ và yêu cầu chỉnh sửa media: `media_assets`, `media_jobs`, `media_edit_requests` |
| `evidence_source_policy.py` | Chính sách tin cậy nguồn: `evidence_source_policies` |
| `trend_report.py` | Báo cáo, evidence, claim và liên kết: `trend_reports`, `trend_report_evidence`, `trend_report_claims`, `trend_report_claim_evidence` |
| `trend_monitor.py`, `trend_alert.py` | Cấu hình theo dõi, snapshot và alert: `trend_monitors`, `trend_snapshots`, `trend_alerts` |
| `advertising_angle.py`, `advertising_brief.py` | Góc quảng cáo, brief và snapshot chỉ số: `advertising_angles`, `advertising_briefs`, `campaign_metric_snapshots` |

## 4.2. Các bảng trong schema hiện tại

Danh sách dưới đây là **34 bảng ứng dụng trong model**; `alembic_version` là bảng điều khiển migration riêng, không tính vào 34 bảng. Một số bảng thuộc chức năng RSS/Trend đã ẩn trên giao diện hoặc Media Studio đang phát triển: schema và dữ liệu lịch sử vẫn được giữ, không có nghĩa các chức năng đó đang sẵn sàng sử dụng.

| Bảng | Mục đích | Quan hệ chính |
| --- | --- | --- |
| `users` | Tài khoản, password hash, provider, token version | 1-n conversations, brands, sessions, tokens |
| `user_settings` | Default platform/tone/language/length/export | 1-1 user |
| `user_sessions` | Thiết bị/phiên đăng nhập, revoke và expiry | n-1 user |
| `email_verification_tokens` | OTP xác minh email dạng hash | n-1 user |
| `password_reset_tokens` | OTP/reset token dạng hash, attempt/expiry/used | n-1 user |
| `conversations` | Cuộc hội thoại, title, pin, brand đang chọn | n-1 user, n-1 brand |
| `messages` | User/assistant message, brief JSON, prompt type | n-1 conversation, tùy chọn brand |
| `uploaded_files` | File upload và liên kết message | n-1 conversation, tùy chọn message |
| `brand_profiles` | Brand identity, tone, màu, keywords, forbidden words | n-1 user |
| `brand_assets` | Asset thuộc brand | n-1 brand |
| `brand_content_checks` | Lịch sử điểm brand consistency | n-1 brand/user |
| `ad_templates` | System/custom ad template | tùy chọn user |
| `template_favorites` | Favorite template theo user | n-1 user/template |
| `saved_contents` | Nội dung quảng cáo người dùng lưu | user/conversation/message/brand |
| `content_activities` | Evaluation, variants và hoạt động nội dung | user, tùy chọn saved content |
| `campaigns` | Chiến dịch và product/objective/platform | n-1 user/brand |
| `campaign_contents` | Nối campaign với saved content, có primary | campaign/saved content |
| `content_documents` | Tài liệu editor, status, version, campaign link | user, message, saved content, campaign |
| `content_versions` | Snapshot version của document | n-1 content document/user |
| `voiceover_audios` | Metadata ownership và file information của audio voiceover đã tạo | n-1 user, tùy chọn n-1 message |
| `media_assets` | Asset ảnh/video, metadata, trạng thái và lineage version | n-1 user, tùy chọn conversation/job |
| `media_jobs` | Job tạo media, provider, trạng thái và idempotency metadata | n-1 user, tùy chọn asset |
| `media_edit_requests` | Request chỉnh sửa media, payload hash và trạng thái | n-1 user, tùy chọn asset |
| `evidence_source_policies` | Chính sách tin cậy nguồn evidence theo người dùng | n-1 user |
| `trend_reports` | Báo cáo đã lưu, thời điểm thu thập, trạng thái nguồn và soft delete | n-1 user/conversation |
| `trend_report_evidence` | Bài/evidence, URL và thời điểm xuất bản | n-1 trend report |
| `trend_report_claims` | Nhận định trong báo cáo | n-1 trend report |
| `trend_report_claim_evidence` | Liên kết claim với evidence hỗ trợ | n-1 claim/evidence |
| `trend_monitors` | Cấu hình theo dõi chủ đề đã lưu | n-1 user |
| `trend_snapshots` | Snapshot của monitor | n-1 monitor |
| `trend_alerts` | Bản ghi cảnh báo xu hướng | liên kết monitor/user theo model |
| `advertising_angles` | Góc quảng cáo được lưu từ quy trình liên quan | n-1 user/trend report |
| `advertising_briefs` | Brief quảng cáo được lưu | n-1 user/advertising angle |
| `campaign_metric_snapshots` | Snapshot chỉ số chiến dịch được nhập/lưu | liên kết campaign |

## 4.3. Quan hệ nghiệp vụ

```text
User
 ├── Conversations ── Messages ── UploadedFiles
 │         └────────── BrandProfile (optional)
 ├── BrandProfiles ── BrandAssets / BrandContentChecks
 ├── SavedContents ── ContentActivities
 │        └────────── CampaignContents ── Campaigns
 └── ContentDocuments ── ContentVersions
```

- Quy tắc xóa phụ thuộc foreign key và quan hệ ORM của từng bảng; không mặc định mọi dữ liệu thuộc user đều cascade.
- Xóa brand không xóa message/content; foreign key brand dùng `SET NULL` ở nơi phù hợp.
- Xóa conversation cascade messages/upload/saved content theo model.
- `campaign_contents` không cho trùng `campaign_id + saved_content_id`.
- Mỗi campaign tối đa một `content_documents.is_campaign_primary = true` nhờ partial unique index `uq_content_documents_campaign_primary`.
- Mỗi user tối đa một brand mặc định nhờ partial unique index `uq_brand_profiles_one_default`.
- Một saved content không lặp cùng `user_id + message_id`.
- Một document không có hai version cùng `content_id + version_number`.
- `voiceover_audios.user_id` bảo vệ quyền truy cập audio theo owner; `message_id` chỉ là liên kết tùy chọn tới message nguồn.

## 4.4. Trường dữ liệu đáng chú ý

### `users`

`id`, `username`, `email`, `hashed_password`, `created_at`, `token_version`, `auth_provider`, `google_sub`, `avatar_url`, `email_verified`.

### `messages`

`id`, `conversation_id`, `brand_id`, `role`, `content`, `created_at`, `ad_brief_json`, `prompt_type`. `role` là `user` hoặc `assistant`; brief được lưu JSON text.

### `saved_contents`

`id`, `user_id`, `conversation_id`, `brand_id`, `message_id` nullable, `title`, `content`, `platform`, `created_at`. `message_id` nullable để hỗ trợ lưu biến thể không gắn trực tiếp message gốc.

### `content_documents` và `content_versions`

Document giữ bản hiện hành; version giữ snapshot title/content/CTA/hashtags/notes, `change_summary`, `created_by` và `created_by_user_id`. `current_version` ở document trỏ số version hiện tại.

### `voiceover_audios`

Bảng lưu `audio_id`, `filename`, `user_id`, `message_id` tùy chọn, kích thước, thời lượng, `voice_id` và `created_at`. `audio_id` và `filename` là duy nhất. `user_id` có foreign key `ON DELETE CASCADE`; `message_id` dùng `ON DELETE SET NULL` để xóa message không làm mất metadata ownership của audio. Protected audio endpoint chỉ phục vụ file khi xác định được owner an toàn.

### Báo cáo RSS/Trend và Media Studio đã giữ schema

`trend_reports` lưu `generated_at`, `retrieved_at`, `source_statuses_json`, `deleted_at`; `trend_report_evidence.published_at` là thời điểm **bài báo xuất bản**, không phải thời điểm thu thập báo cáo. Claim liên kết evidence qua `trend_report_claim_evidence`. Các bảng này còn để giữ tương thích và lịch sử dù lối vào RSS/Trend đã ẩn. `media_assets`, `media_jobs`, `media_edit_requests` vẫn lưu metadata/lịch sử cho Media Studio đang phát triển; sự tồn tại của bảng không chứng minh nút tạo ảnh/video đang hoạt động.

## 4.5. Migration chain

| Revision | Nội dung |
| --- | --- |
| `20260727_0001` | Initial schema |
| `20260727_0002` | Ad templates và favorites |
| `20260727_0003` | Google auth fields |
| `20260727_0004` | Password reset |
| `20260727_0005` | Email verification và user sessions |
| `20260727_0006` | Brand profiles/assets/checks |
| `20260727_0007` | Content editor và versions |
| `20260727_0008` | Partial unique index cho campaign primary |
| `20260727_0009`–`0011` | Tên nền tảng tùy chỉnh trong các bảng liên quan |
| `20260727_0012` | Media assets |
| `20261001_0013`–`0016` | Metadata video, media jobs, asset roots và edit requests |
| `20261003_0017` | Ownership metadata cho generated voiceover audio |
| `20261005_0018`–`0019` | Evidence, claim và trạng thái nguồn của trend report |
| `20261006_0020` | Chính sách nguồn Product Trust |
| `20261006_0021`–`0022` | Monitor, snapshot và alert |
| `20261006_0023`–`0024` | Advertising angles, briefs và campaign metrics |
| `20261006_0025` | Soft delete cho lịch sử trend report |

Các hàng gộp vẫn đại diện cho từng revision riêng; mã migration đầy đủ nằm ở `backend/alembic/versions/`. Trước production migration cần backup database; không dùng `Base.metadata.drop_all()` hoặc xóa SQLite để cập nhật schema.

## 4.6. Backup và dữ liệu file

Database không chứa bytes file upload/voiceover; model chỉ lưu path và metadata. Docker Compose dùng named volumes `postgres_data` và `upload_data`. Nền tảng có filesystem tạm phải gắn persistent disk hoặc chuyển `file_storage` sang object storage.

### Metadata nền tảng

`messages`, `saved_contents`, `ad_templates`, `content_documents` và `campaigns` có thêm `platform_name` nullable. `user_settings` có `default_platform_name` nullable. Các cột này chỉ bổ sung dữ liệu, không xóa giá trị `prompt_type`/`platform` cũ; các migration `20260727_0009`, `20260727_0010`, `20260727_0011` mô tả việc nâng cấp schema. Startup hiện không tự nâng cấp SQLite legacy.

Với dữ liệu cũ, `platform_name` có thể null và UI dùng nhãn tương thích legacy. Với bản ghi mới có `platform = other`, backend yêu cầu `platform_name` dài 2–80 ký tự sau chuẩn hóa.
## 4.7. Bootstrap và ownership audio

Migration `20261003_0017_voiceover_audio_ownership` thêm bảng `voiceover_audios`, liên kết mỗi file voiceover với user tạo file và message tùy chọn. File không có metadata owner không được tự gán trong quá trình nâng cấp; endpoint protected sẽ từ chối file legacy đó.

Database rỗng phải dùng bootstrap explicit đã validate (`app.database.bootstrap` hoặc `app.database.prepare_database`). Database có dữ liệu phải backup và nâng cấp bằng Alembic; schema lệch hoặc không rõ lịch sử bị fail-closed. Không sửa migration cũ, stamp để che mismatch, drop bảng hoặc xóa database.

## 4.8. Đồng bộ persistence sau rà soát

### Voiceover audio

voiceover_audios là metadata ownership, không phải nơi lưu bytes audio. File thực tế nằm trong audio storage; bản ghi giữ audio_id, filename, owner, message link, size, duration và voice id. Router protected chỉ trả file khi bản ghi thuộc user hiện tại.

persist_latest_voiceover() và persist_latest_voiceover_record() đảm bảo một message chỉ giữ audio voiceover mới nhất. Quy trình là tạo/kiểm tra output mới, lưu bản ghi mới, xóa metadata cũ cùng message và dọn file cũ sau khi commit. Nếu xóa file vật lý gặp lỗi, metadata mới vẫn được giữ đúng; orphan cleanup có thể xử lý riêng.

### Quan hệ với message và conversation

- message_id của voiceover là liên kết tùy chọn; khi có giá trị, backend kiểm tra message thuộc conversation của user hiện tại.
- Audio voiceover không làm thay đổi nội dung message gốc, brief, transcript hay reference file.
- File upload/reference/PCM tạm không lưu bytes vào database và phải cleanup sau request.
- Tạo audio mới trong cùng message thay audio cũ; F5 hoặc tải lại trang không làm mất kết quả nếu frontend lấy lại audio theo message/record đã persist.

### Database safety contract

```text
startup → kiểm tra schema chuẩn → cho phép ứng dụng phục vụ request
request → auth/ownership → service transaction → commit metadata
        → dọn file cũ/tạm nếu luồng xử lý có thao tác file
```

Database hiện vẫn được bảo vệ bởi schema manifest, schema validator, bootstrap explicit và Alembic head 20261006_0025. Không xóa database cũ, không stamp để che drift và không sửa migration đã áp dụng.
