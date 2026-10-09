# 4. Cơ sở dữ liệu

> Trạng thái canonical hiện tại: **34 bảng ứng dụng**, Alembic head `20261006_0025_trend_report_history_soft_delete`.

## 4.1. Database runtime

- URL nằm ở `DATABASE_URL`.
- SQLite local/test chuẩn hóa đường dẫn tương đối về thư mục backend và bật foreign key pragma.
- PostgreSQL dùng driver `postgresql+psycopg` và là lựa chọn production.
- SQLAlchemy session được cấp qua `get_db()` và đóng sau mỗi request.
- SQLite legacy được `initialize_database()` bổ sung cột thiếu bảo toàn dữ liệu; PostgreSQL không chạy nhánh này.

## 4.2. Danh sách bảng

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
| `trend_reports` | Report, query, summary, source status, Product Trust và lịch sử | n-1 user, tùy chọn conversation/message |
| `trend_report_evidence` | Evidence có citation, URL, publisher, freshness và verification metadata | n-1 trend report |
| `trend_report_claims` | Claim được đánh giá trong report | n-1 trend report |
| `trend_report_claim_evidence` | Liên kết claim với evidence | claim/evidence |
| `evidence_source_policies` | Chính sách trusted/excluded theo user và source | n-1 user |
| `trend_monitors` | Chủ đề theo dõi, cadence, timezone và next run | n-1 user, tùy chọn trend report |
| `trend_snapshots` | Kết quả từng lần thu thập, run key, status, freshness và payload | n-1 monitor |
| `trend_alerts` | Alert theo monitor/claim, lifecycle và severity | n-1 user/monitor, tùy chọn snapshot |
| `advertising_angles` | Góc quảng cáo có provenance claim/evidence và trust action | n-1 user/trend report |
| `advertising_briefs` | Brief được tạo từ angle đủ điều kiện | n-1 user/angle |
| `campaign_metric_snapshots` | Số liệu thực tế theo campaign và thời điểm ghi nhận | n-1 user/campaign, tùy chọn brief |
| `media_assets` | Asset ảnh/video, metadata, trạng thái và lineage version | n-1 user, tùy chọn conversation/job |
| `media_jobs` | Job tạo media, provider, trạng thái và idempotency metadata | n-1 user, tùy chọn asset |
| `media_edit_requests` | Request chỉnh sửa media, payload hash và trạng thái | n-1 user, tùy chọn asset |

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

- Xóa user cascade xuống dữ liệu thuộc user.
- Xóa brand không xóa message/content; foreign key brand dùng `SET NULL` ở nơi phù hợp.
- Xóa conversation cascade messages/upload/saved content theo model.
- `campaign_contents` không cho trùng `campaign_id + saved_content_id`.
- Mỗi campaign tối đa một `content_documents.is_campaign_primary = true` nhờ partial unique index `uq_content_documents_campaign_primary`.
- Mỗi user tối đa một brand mặc định nhờ partial unique index `uq_brand_profiles_one_default`.
- Một saved content không lặp cùng `user_id + message_id`.
- Một document không có hai version cùng `content_id + version_number`.
- `voiceover_audios.user_id` bảo vệ quyền truy cập audio theo owner; `message_id` chỉ là liên kết tùy chọn tới message nguồn.
- Trend Report, Monitor, Snapshot, Alert, Angle, Brief và Metric Snapshot đều có owner/FK hoặc quan hệ owner-scoped; service không cho đọc/ghi chéo user.
- `trend_reports.deleted_at` là soft-delete lịch sử; evidence, angle, brief, campaign và metric không bị xóa khi user dọn lịch sử report.
- `trend_snapshots` unique theo `monitor_id + run_key`; `trend_alerts.active_key` unique để ngăn duplicate active incident.

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

### Trend Radar và downstream artifacts

`trend_reports` chứa query/summary, source status, Product Trust và `deleted_at`; các bảng evidence/claim giữ provenance và quan hệ citation. `trend_monitors` lưu cadence/timezone/next run nhưng không tự tạo worker hoặc production cron. `trend_snapshots` lưu cả SUCCESS, EMPTY và ERROR để phản ánh execution history; Alert Engine chỉ đánh giá SUCCESS hợp lệ.

`advertising_angles` giữ claim/evidence source và trust action. `advertising_briefs` tham chiếu angle; `campaigns` có thể tham chiếu Trend Report/Brief; `campaign_metric_snapshots` lưu payload metric do caller cung cấp. Các quan hệ này được giữ lại khi Trend Report bị soft-delete.

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
| `20261003_0017` | Ownership metadata cho generated voiceover audio |
| `20261005_0018` | Trend Report evidence store và claim/evidence links |
| `20261005_0019` | Per-source/platform status cho Trend Report |
| `20261006_0020` | Product Trust JSON và source policies |
| `20261006_0021` | Trend Monitor và Trend Snapshot foundation |
| `20261006_0022` | Trend Alert Engine và active-key uniqueness |
| `20261006_0023` | Advertising Angle provenance/trust gate |
| `20261006_0024` | Advertising Brief, Campaign link và Campaign Metric Snapshot |
| `20261006_0025` | Soft-delete lịch sử Trend Report bằng `deleted_at` |

Migration nằm ở `backend/alembic/versions/`. Trước production migration cần backup database; không dùng `Base.metadata.drop_all()` hoặc xóa SQLite để cập nhật schema.

## 4.6. Backup và dữ liệu file

Database không chứa bytes file upload/voiceover; model chỉ lưu path và metadata. Docker Compose dùng named volumes `postgres_data` và `upload_data`. Nền tảng có filesystem tạm phải gắn persistent disk hoặc chuyển `file_storage` sang object storage.

### Metadata nền tảng

`messages`, `saved_contents`, `ad_templates`, `content_documents` và `campaigns` có thêm `platform_name` nullable. `user_settings` có `default_platform_name` nullable. Các cột này chỉ bổ sung dữ liệu, không xóa giá trị `prompt_type`/`platform` cũ; migration `20260727_0009`, `20260727_0010`, `20260727_0011` và cơ chế nâng cấp SQLite đều không phá hủy.

Với dữ liệu cũ, `platform_name` có thể null và UI dùng nhãn tương thích legacy. Với bản ghi mới có `platform = other`, backend yêu cầu `platform_name` dài 2–80 ký tự sau chuẩn hóa.
## 4.7. Bootstrap và ownership audio

Migration `20261003_0017_voiceover_audio_ownership` thêm bảng `voiceover_audios`, liên kết mỗi file voiceover với user tạo file và message tùy chọn. File không có metadata owner không được tự gán trong quá trình nâng cấp; endpoint protected sẽ từ chối file legacy đó.

Database rỗng phải dùng bootstrap explicit đã validate (`app.database.bootstrap` hoặc `app.database.prepare_database`). Database có dữ liệu phải backup và nâng cấp bằng Alembic; schema lệch hoặc không rõ lịch sử bị fail-closed. Không sửa migration cũ, stamp để che mismatch, drop bảng hoặc xóa database.
