# 2. Chức năng hệ thống

## 2.1. Bản đồ chức năng

| Nhóm | Chức năng đang có | Backend chính | Frontend chính |
| --- | --- | --- | --- |
| Tài khoản | Đăng ký, login local, Google Login tùy chọn, email verification, quên/reset password OTP, logout phiên | `auth.py`, `auth_service.py`, token services | Login, Register, VerifyEmail, ForgotPassword, ResetPassword, ActiveSessions |
| Chat AI | CRUD hội thoại, ghim, đổi tên, gửi message, stream, sửa và sinh lại phản hồi | `conversation.py`, `message.py`, `message_service.py` | Chat, nhóm `chat/*`, `useChat`, `useConversation` |
| Brief quảng cáo | Nhập sản phẩm, đối tượng, mục tiêu, platform, tone, ngôn ngữ, độ dài | `schemas/message.py`, `prompts/ad_brief.py` | `AdBriefForm` |
| Nền tảng nội dung | Facebook, TikTok, Instagram, Shopee, Google Ads và Khác; mục Khác bắt buộc tên nơi đăng | `platforms.py`, `prompt_service.py`, `message_service.py` | PromptSelector, AdBriefForm, Campaign và Template |
| Thương hiệu | CRUD brand, chọn brand, asset, consistency check, thống kê | `brand.py`, `brand_service.py`, `brand_prompt.py` | Brands, BrandSelector, BrandConsistencyPanel |
| Template | System/custom template, tạo/sửa/xóa custom, favorite | `template.py`, `template_service.py` | Templates, TemplateQuickStart |
| Nội dung đã lưu | Lưu, xem thư viện, xóa, activity | `saved_content.py`, `saved_content_service.py` | Library, SavedContentPanel |
| Campaign | CRUD campaign, gắn saved content, chọn primary | `campaign.py`, `campaign_service.py` | Campaigns, CampaignDetail |
| Content editor | Document, version history, compare, restore, AI rewrite | `content_document.py`, `content_document_service.py` | ContentEditor, Version panels |
| Chất lượng nội dung | Điểm theo 9 tiêu chí, tạo 3 biến thể A/B/C, activity | `content.py`, evaluation/variant services | ContentScorePanel, VariantGeneratorModal |
| Upload | Đính kèm image/video/PDF/text, kiểm tra MIME/kích thước/quyền | `upload.py`, `upload_service.py` | ChatInput, AttachmentPreview |
| Dashboard | Summary, activity theo ngày, platform usage | `dashboard.py`, `dashboard_service.py` | Dashboard, ActivityChart, PlatformChart |
| Voice Studio | Liệt kê voice, clean script, tạo/tải audio | `voiceover.py`, `voiceover_service.py` | VoiceoverModal |
| User settings | Profile, đổi password, AI defaults, theme, export defaults | `user.py`, `user_service.py` | Profile, Settings, ThemeContext |

## 2.2. Chat và tạo nội dung

1. Người dùng chọn hoặc tạo conversation.
2. Có thể chọn brand, template hoặc điền `AdBrief`.
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