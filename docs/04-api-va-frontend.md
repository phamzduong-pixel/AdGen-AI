# 5. API và frontend

## 5.1. Nhóm API

Tất cả endpoint ngoài `/` và `/health` cần JWT theo `get_current_user`, trừ endpoint auth công khai phù hợp.

| Prefix | Trách nhiệm | Endpoint tiêu biểu |
| --- | --- | --- |
| `/auth` | đăng ký/login/Google/email reset/session | `POST /register`, `/login`, `/google`, `/forgot-password`, `GET /me` |
| `/users/me` | profile, password, settings | `GET/PATCH /`, `POST /change-password`, `GET/PUT /settings` |
| `/conversations` | CRUD, pin, title, brand | `POST`, `GET`, `PUT`, `DELETE`, các `PATCH` |
| `/messages` | message, history, stream, regenerate | `POST`, `GET /{conversation_id}`, `POST /stream`, `PUT /{message_id}/stream` |
| `/uploads` | upload/list/download/delete | `POST /{conversation_id}`, `GET /file/{id}/download` |
| `/media` | media asset/job, generation, edit, versions và download | create/edit/status/download/delete asset theo contract Media Studio |
| `/brands` | brand profile, asset, consistency | CRUD, check, upload/download asset |
| `/templates` | system/custom template, favorite | CRUD custom, favorite/unfavorite |
| `/saved-contents` | lưu, đọc, xóa content | create/list/delete |
| `/content` | evaluate và generate variants | `POST /evaluate`, `POST /generate-variants` |
| `/contents` | editor document/version/rewrite | CRUD, versions, restore, rewrite |
| `/campaigns` | campaign và content links | CRUD, add/remove, primary content |
| `/dashboard` | summary/activity/platform usage | `GET /summary`, `/activity`, `/platform-usage` |
| `/voiceover` | voices, clean script, system/reference TTS và protected audio | `GET /voices`, `POST /clean-script`, `/generate`, `/generate-reference`, `GET/HEAD /audio/{filename}` |
| `/stt` | nhận dạng lời nói từ audio/video | `POST /transcribe`, `POST /transcribe-video` |
| `/voice-conversion` | Direct Voice Conversion và video remux | `POST /convert`, `/convert-reference`, `/convert-reference-video` |
| `/trend-reports` | retrieve/list/get/delete Trend Report, trust summary, source policy | `POST /retrieve`, `POST`, `GET`, `DELETE /{report_key}`, `GET /{report_key}/trust`, `GET/PUT /source-policies` |
| `/insight-campaign` | Trend Monitor/Snapshot/Alert overview, Brief, Campaign và metric snapshot | `GET /overview`, `POST /advertising-angles/{id}/brief`, `POST /briefs/{id}/campaign`, `GET/POST /campaigns/{id}/metric-snapshots` |

Danh sách chi tiết nên kiểm tra trực tiếp trong `backend/app/api/`; bảng trên là bản đồ nghiệp vụ, không thay thế OpenAPI.

## 5.2. Quy ước request frontend

- Base URL: `VITE_API_URL`, không có slash cuối.
- Axios client ở `frontend/src/services/api/axios.js` gắn JWT từ storage.
- API module tách theo domain: `chatApi.js`, `campaignApi.js`, `contentEditorApi.js`, `voiceoverApi.js`...
- Upload dùng `multipart/form-data`; file được gắn vào message bằng ID sau khi upload.
- Stream dùng Fetch API để đọc body từng chunk và hỗ trợ AbortController.
- Response lỗi được chuẩn hóa qua `frontend/src/utils/apiError.js`.
- Voiceover dùng cùng contract trích xuất `VoiceoverScriptExtractor` cho bước làm sạch script và generation; frontend giữ riêng văn bản gốc/văn bản đã lọc khi người dùng chuyển phiên bản trong Voice Studio.
- Khi chế độ file có transcript, frontend gửi đúng transcript hiện tại sang TTS. Khi transcript trống, `voiceoverApi.js` gọi Direct Voice Conversion bằng file source và preset/custom reference; không tự tạo text.

## 5.3. Route giao diện

Các route chính trong `frontend/src/routes/AppRoutes.jsx` gồm:

`/login`, `/register`, `/verify-email`, `/forgot-password`, `/verify-reset-code`, `/reset-password`, `/chat`, `/dashboard`, `/library`, `/templates`, `/campaigns`, `/campaigns/:campaignId`, `/contents/:contentId`, `/brands`, `/profile`, `/settings` và fallback Not Found.

Route workspace được bảo vệ bởi `ProtectedRoute`. `MainLayout`, `WorkspaceLayout` và `ChatLayout` cung cấp bố cục dùng chung.

## 5.4. Mapping frontend/backend

| Hook/UI | API module | Backend domain |
| --- | --- | --- |
| `useChat`, `useConversation` | `chatApi`, `conversationApi`, `messageApi` | conversations/messages |
| `useBrands` / Brand selector | `brandApi` | brands |
| Campaign pages | `campaignApi` | campaigns |
| Library/Saved content | `savedContentApi` | saved-contents |
| Templates | `templateApi` | templates |
| Content editor | `contentEditorApi` | contents |
| Score/variants | `contentToolsApi` | content |
| Dashboard | `dashboardApi` | dashboard |
| Attachments | `uploadApi` | uploads |
| Voiceover modal | `voiceoverApi` | voiceover, stt, voice-conversion |
| Trend Report panel | `trendReportApi`, `trendReportMessage`, `trendReportTrust`, `trendReportSourceStatus` | trend-reports, insight-campaign |

## 5.5. Bảo mật tích hợp

- CORS phải chứa đúng origin frontend, không wildcard khi `allow_credentials=True`.
- Google credential chỉ gửi backend để verify; không lưu credential Google trong local storage.
- File download phải đi qua endpoint protected.
- Backend luôn lọc dữ liệu theo `current_user.id`; frontend không được xem ID là quyền truy cập.
- Trend Report delete là soft-delete theo owner; downstream evidence, angle, brief, campaign và metric snapshot không bị xóa theo lịch sử hiển thị.
- Trend Report panel nằm trong Chat, không phải một search engine độc lập; Product Trust/backend là nguồn sự thật cho status, evidence, policy và action.

## 5.6. Contract nền tảng

Các request tạo message thường và stream nhận `prompt_type` cùng `platform_name`; `ad_brief.platform` và `ad_brief.platform_name` được giữ xuyên suốt. Template, saved content, content document, campaign, evaluation/variants và settings dùng cùng cặp trường. `platform_name` chỉ được chấp nhận như input dữ liệu, được giới hạn 2–80 ký tự và chuẩn hóa khoảng trắng.

Frontend không đưa Email, Landing Page, SEO, Slogan, Viết lại hoặc Tóm tắt vào bộ chọn nền tảng mới. Các giá trị legacy vẫn được render khi mở bản ghi cũ, nhưng không được tạo mới từ selector; thao tác Viết lại/Tóm tắt không bị xóa khỏi editor/action flow.

## 5.7. Stream disconnect và layout chat

`POST /messages/stream` và `PUT /messages/{message_id}/stream` giữ `text/plain; charset=utf-8`. `_stream_with_disconnect()` kiểm tra ASGI disconnect và đóng generator local; không thêm endpoint cancellation hay cam kết remote cancellation.

Resize sidebar chỉ là UI tại `ChatLayout`, không thay đổi `chatApi.js`/`useChat.js` hay request/response contract.
