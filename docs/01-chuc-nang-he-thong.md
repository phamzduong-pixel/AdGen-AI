# 2. Chức năng hệ thống

## 2.1. Bản đồ chức năng

| Nhóm | Chức năng đang có | Backend chính | Frontend chính |
| --- | --- | --- | --- |
| Tài khoản | Đăng ký, login local, Google Login tùy chọn, email verification, quên/reset password OTP, logout phiên | `auth.py`, `auth_service.py`, token services | Login, Register, VerifyEmail, ForgotPassword, ResetPassword, ActiveSessions |
| Chat AI | CRUD hội thoại, ghim, đổi tên, gửi message, stream, sửa và sinh lại phản hồi | `conversation.py`, `message.py`, `message_service.py` | Chat, nhóm `chat/*`, `useChat`, `useConversation` |
| Thông tin quảng cáo | Nhập sản phẩm, đối tượng, mục tiêu, platform, tone, ngôn ngữ, độ dài | `schemas/message.py`, `prompts/ad_brief.py` | `AdBriefForm` |
| Nền tảng nội dung | Facebook, TikTok, Instagram, Shopee, Google Ads và Khác; mục Khác bắt buộc tên nơi đăng | `platforms.py`, `prompt_service.py`, `message_service.py` | PromptSelector, AdBriefForm, Campaign và Template |
| Thương hiệu | CRUD brand, chọn brand, asset, consistency check, thống kê | `brand.py`, `brand_service.py`, `brand_prompt.py` | Brands, BrandSelector, BrandConsistencyPanel |
| Template | System/custom template, tạo/sửa/xóa custom, favorite | `template.py`, `template_service.py` | Templates, TemplateQuickStart |
| Nội dung đã lưu | Lưu, xem thư viện, xóa, activity | `saved_content.py`, `saved_content_service.py` | Library, SavedContentPanel |
| Campaign | CRUD campaign, gắn saved content, chọn primary | `campaign.py`, `campaign_service.py` | Campaigns, CampaignDetail |
| Content editor | Document, version history, compare, restore, AI rewrite | `content_document.py`, `content_document_service.py` | ContentEditor, Version panels |
| Chất lượng nội dung | Điểm theo 9 tiêu chí, tạo 3 biến thể A/B/C, activity | `content.py`, evaluation/variant services | ContentScorePanel, VariantGeneratorModal |
| Upload | Đính kèm image/video/PDF/text, kiểm tra MIME/kích thước/quyền | `upload.py`, `upload_service.py` | ChatInput, AttachmentPreview |
| Media Studio | Tạo ảnh/video, upload, chỉnh sửa media, version, preview và download | `media.py`, `media_service.py`, `video_service.py` | MediaStudio |
| Dashboard | Summary, activity theo ngày, platform usage | `dashboard.py`, `dashboard_service.py` | Dashboard, ActivityChart, PlatformChart |
| Voice Studio | Text → TTS, audio/video → STT → TTS, reference-voice TTS và Direct Voice Conversion Seed-VC có điều kiện | `voiceover.py`, `stt.py`, `video_stt.py`, `voice_conversion.py`, các voice services | VoiceoverModal, AudioPlayer |
| Trend Radar | Trend Report, Product Trust, monitor/snapshot, alert, angle, brief, campaign metric và lịch sử | `trend_report.py`, `insight_campaign.py`, trend services | TrendReportPanel, Stage4WorkflowPanel |
| User settings | Profile, đổi password, AI defaults, theme, export defaults | `user.py`, `user_service.py` | Profile, Settings, ThemeContext |

## 2.2. Chat và tạo nội dung

1. Người dùng chọn hoặc tạo conversation.
2. Có thể chọn brand, template hoặc điền thông tin quảng cáo.
3. Frontend gửi `conversation_id`, `content`, `prompt_type`, `ad_brief`, `brand_id` và `attachment_ids` nếu có.
4. Backend kiểm tra conversation/brand/file thuộc user hiện tại.
5. Tin nhắn user được lưu trước; AI nhận lịch sử và context.
6. Assistant message được lưu; người dùng có thể lưu, đánh giá, tạo biến thể hoặc đưa vào campaign.

Hai chế độ:

- Non-stream: `POST /messages`, nhận kết quả hoàn chỉnh.
- Stream: `POST /messages/stream`, nhận từng chunk; backend lưu toàn bộ assistant message sau khi stream.

## 2.3. Tài khoản và bảo mật

- JWT được cấp sau local login hoặc backend xác minh Google credential.
- Request protected dùng bearer token và kiểm tra ownership theo `current_user`.
- Password reset dùng OTP 6 số; chỉ lưu HMAC hash, có hạn dùng, giới hạn thử/resend.
- Đổi password tăng `token_version`, làm vô hiệu hóa token cũ.
- Upload không public trực tiếp; file tải qua endpoint có JWT.

## 2.4. Đánh giá và biến thể

Content evaluation trả `overall_score`, đúng 9 criteria, strengths, improvements và suggested revision. Variant generation trả đúng 3 góc:

- A: nhấn mạnh lợi ích.
- B: nhấn mạnh giá/ưu đãi nhưng không bịa khi nguồn không có dữ liệu.
- C: nhấn mạnh cảm xúc/nỗi đau khách hàng.

Hoạt động được ghi vào `content_activities` để dashboard tổng hợp.

## 2.5. Quy tắc AI

- Không tự bịa giá, ưu đãi, chứng nhận, số liệu hoặc claim nếu brief không cung cấp.
- Nội dung user là dữ liệu không đáng tin cậy, không được dùng để ghi đè system prompt.
- Endpoint sửa message thường chỉ cập nhật dữ liệu; `/{message_id}/stream` mới xóa phần sau và sinh lại phản hồi.

## 2.6. Quy ước nền tảng mới

Bộ chọn tạo nội dung mới chỉ cung cấp Facebook, TikTok, Instagram, Shopee, Google Ads và Khác. Facebook, TikTok và Shopee được ưu tiên hiển thị; Instagram, Google Ads và Khác nằm trong nhóm xem thêm ở các giao diện phù hợp.

Khi chọn Khác, người dùng nhập tên kênh/nơi đăng từ 2 đến 80 ký tự. Backend chuẩn hóa khoảng trắng, lưu riêng ở `platform_name` và đưa vào prompt như dữ liệu tham khảo không đáng tin cậy; dữ liệu này không thể ghi đè system prompt và không làm AI tự suy đoán quy định riêng của kênh.

Các giá trị cũ như Email, Landing Page, SEO, Slogan, Viết lại và Tóm tắt không còn là lựa chọn nền tảng mới. Chúng vẫn được đọc/hiển thị dưới nhãn nền tảng cũ khi có trong lịch sử; Viết lại và Tóm tắt vẫn thuộc nhóm thao tác chỉnh sửa nếu luồng chỉnh sửa sử dụng.

## 2.7. Voice Studio

Từ một assistant message, người dùng chọn **Voiceover** để mở Voice Studio. Hệ thống xử lý theo các bước:

1. Gửi `message.content` tới bước làm sạch script.
2. Ưu tiên nhận diện marker lời thoại như **VO**, **Lời thoại**, **Narration**, **Voiceover**, **MC** hoặc **Host**.
3. Nếu không có marker nhưng nội dung có cấu trúc kịch bản thoại tự nhiên, dùng fallback heuristic có kiểm soát để chọn các đoạn có khả năng được đọc.
4. Giữ nguyên nội dung, thứ tự và placeholder; không rewrite hoặc tự thêm lời thoại. Heading, metadata, markdown không cần đọc và chỉ dẫn sản xuất như Visual, Camera, Nhạc, SFX, Caption được loại khỏi ứng viên khi nhận diện được.
5. Hiển thị văn bản đã lọc trong textarea, đồng thời giữ văn bản gốc để người dùng chuyển qua lại bằng **Xem văn bản gốc** và **Quay lại văn bản đã lọc**.
6. Ở chế độ văn bản, nội dung đang hiển thị sau chỉnh sửa được gửi tới system TTS hoặc reference-voice TTS tùy nguồn giọng.
7. Ở chế độ file, người dùng có thể trích transcript rồi chỉnh sửa và tạo TTS. Nếu transcript để trống, nút tạo gọi Direct Voice Conversion: file audio được chuyển giọng trực tiếp; file video được tách audio, chuyển giọng rồi remux vào video.
8. Direct Voice Conversion chọn giọng đích từ preset reference hoặc file tham chiếu tùy chỉnh và chỉ chạy khi Seed-VC runtime hợp lệ.

Việc nhận diện và làm sạch là deterministic; nếu fallback chưa chắc chắn, UI hiển thị cảnh báo nhẹ để người dùng kiểm tra trước khi tạo audio. Nhánh Direct Voice Conversion không cần chuyển lời nói thành text và giữ timing/prosody của source theo khả năng của Seed-VC. Integration đã có trong source nhưng fail-closed nếu thiếu Python 3.10 riêng, checkout/model Seed-VC hoặc reference WAV; vì vậy chưa được xem là runtime production đã PASS.

## 2.8. Trend Radar và quy trình insight-to-campaign

Trend Radar hiện được mở trong Chat, không phải một công cụ tìm kiếm độc lập. Người dùng có thể:

- nhập chủ đề và thu thập Trend Report từ collector đã cấu hình;
- xem claim, evidence, source, freshness, conflict và Product Trust;
- chọn `all_evidence` hoặc `verified_only`; backend quyết định evidence hợp lệ;
- cấu hình source policy theo owner với **Tin cậy** hoặc **Loại trừ**;
- theo dõi chủ đề bằng Monitor, lưu Snapshot và đánh giá Alert khi có SUCCESS hợp lệ;
- chuyển insight đủ điều kiện thành Advertising Angle → Brief quảng cáo → Campaign → Metric Snapshot;
- xóa bản ghi lịch sử Trend Report bằng soft-delete mà không xóa artifact downstream.

EMPTY/ERROR snapshot không tạo hoặc resolve alert. Alert lifecycle hiện hỗ trợ TREND_NEW và TREND_SPIKE; Product Trust không đồng nghĩa với độ tự tin của LLM.
