# 3. Luồng xử lý AI

## 3.1. Luồng chat stream

```text
Frontend Chat
    │ POST /messages/stream
    ▼
Message API
    ├─ xác thực JWT và ownership conversation
    ├─ normalize/validate prompt_type
    ├─ resolve brand và kiểm tra brand thuộc user
    ├─ lưu user message + brief JSON
    ├─ gắn file tạm vào message
    └─ build_history()
             │
             ▼
Context / history
    ├─ lịch sử + ad_brief + attachment metadata
    ├─ follow-up intent nếu là yêu cầu tiếp nối
    └─ product/brand context
             │
             ▼
Prompt service
    ├─ system prompt an toàn
    ├─ specialized prompt theo platform
    ├─ platform intelligence
    ├─ knowledge base
    ├─ trend intelligence
    └─ ad brief/brand rules
             │
             ▼
Gemini 2.5 Flash generate_content_stream()
             │ từng chunk
             ▼
StreamingResponse → frontend ghép hiển thị
             │ kết thúc
             ▼
Lưu assistant message đầy đủ vào messages
```

Implementation chính: `backend/app/services/message_service.py` và `backend/app/services/ai_service.py`.

## 3.2. Chuẩn bị input

`build_history()` đọc message theo `created_at`, sau đó giữ `role`/`content`, parse `ad_brief_json` và đưa attachment của user vào history với filepath, MIME và filename.

`format_history()` chuyển role `user`/`assistant` sang `user`/`model` của Google Gen AI SDK. Attachment được xử lý như sau:

| Loại | Cách gửi Gemini |
| --- | --- |
| Image, video, PDF | đọc bytes và gửi `Part.from_bytes` |
| Text | đọc tối đa 50.000 ký tự và gửi như text context |
| Loại khác | thông báo file đã lưu nhưng chưa đọc được |

Brief được nối vào nội dung user message bằng `format_ad_brief()`; dữ liệu user vẫn nằm ngoài system instruction.

## 3.3. Nhận diện yêu cầu tiếp nối

`ConversationContextService` và `FollowUpIntentResolver` nhận diện:

- `shorten`, `expand`, `change_tone`, `add_cta`;
- `rewrite`, `multi_variation`, `switch_platform`;
- `fix_content`, `general_refinement`, `generate_voiceover`, `new_request`.

Engine tìm brief gần nhất, lấy câu trả lời assistant gần nhất và suy ra platform/tone/variation count. `ContextPruner` có thể giữ message đầu tiên cùng tối đa 3 cặp hội thoại gần nhất để tránh context quá dài.

## 3.4. Ghép prompt

`build_system_prompt()` trong `prompt_service.py`:

1. Chuẩn hóa `prompt_type` và alias như `fb → facebook`, `ig → instagram`, `google-ads → google_ads`.
2. Thêm `SYSTEM_PROMPT` và prompt chuyên biệt từ `backend/app/prompts/`.
3. Thêm platform specification: mục tiêu, hành vi, cấu trúc, hook, CTA, giới hạn, best practice và policy.
4. Thêm knowledge context dựa trên platform, product và brand.
5. Thêm trend context đã được service cung cấp; không có dữ liệu thì yêu cầu AI không bịa trend.
6. Thêm ad brief rules và brand rules.

Các nền tảng tạo mới được map: `facebook`, `tiktok`, `instagram`, `shopee`, `google_ads`, `other`. Các map legacy như `youtube`, `email`, `landing_page`, `seo`, `slogan`, `rewrite`, `summarize` chỉ giữ để đọc/xử lý dữ liệu cũ, không xuất hiện trong selector tạo mới.

## 3.5. Non-stream và structured AI

`ask_ai()` gọi `generate_content()` cho output hoàn chỉnh, sau đó:

1. Chạy `output_validation_service.validate_and_sanitize()`.
2. Ghi generation record vào `backend/data/learning_dataset.jsonl`; lỗi logging không làm hỏng response chính.
3. Trả nội dung cho `message_service` để lưu assistant message.

Evaluation/variants dùng JSON response và parse bằng Pydantic. JSON sai schema trả `502`; quota/rate limit trả `429`.

## 3.6. Xử lý lỗi stream

- Lỗi quota/429 trả marker `[ADGEN_QUOTA_ERROR]`; lỗi khác trả `[ADGEN_STREAM_ERROR]`.
- Nếu đã nhận một phần nội dung, phần đã ghép vẫn được lưu.
- Reverse proxy cần tắt response buffering (`X-Accel-Buffering: no`) và giữ request đủ lâu.
- Frontend dùng AbortController để hủy stream.

## 3.7. Luồng đánh giá/biến thể

```text
message_id hoặc saved_content_id hoặc raw content
        │
        ▼
resolve_content_source()
        │ lấy platform/audience/tone từ request hoặc nguồn gốc
        ▼
request_structured_ai()
        ├─ generate_structured_content()
        ├─ parse Pydantic response
        └─ map quota/schema error → HTTP error
        ▼
record_content_activity()
        ▼
JSON response cho frontend
```

## 3.8. Voiceover

Voiceover có adapter provider trong `backend/app/services/voiceover/providers/`. Luồng gồm làm sạch script, chọn voice, gọi Edge TTS hoặc mock provider tùy cấu hình, lưu audio và trả URL protected `/voiceover/audio/{filename}`.

## 3.9. Nền tảng và custom platform

`prompt_type` được chuẩn hóa theo sáu nền tảng hiện hành: `facebook`, `tiktok`, `instagram`, `shopee`, `google_ads`, `other`. Với `other`, `platform_name` được chuẩn hóa và đặt trong khối dữ liệu tham khảo của prompt. Nội dung này không phải chỉ dẫn, không thay thế system prompt và chỉ dùng để tạo quảng cáo chung phù hợp brief khi thiếu thông tin đặc thù.

Normal và stream dùng cùng quy trình validation, lưu `prompt_type`/`platform_name` ở message user và assistant. Các message cũ vẫn dùng được nhờ nhánh tương thích legacy; không có migration xóa hoặc chuyển đổi dữ liệu cũ.