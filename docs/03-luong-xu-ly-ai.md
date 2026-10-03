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

| Loại              | Cách gửi Gemini                                 |
| ----------------- | ----------------------------------------------- |
| Image, video, PDF | đọc bytes và gửi `Part.from_bytes`              |
| Text              | đọc tối đa 50.000 ký tự và gửi như text context |
| Loại khác         | thông báo file đã lưu nhưng chưa đọc được       |

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

Normal và stream dùng chung quy trình chuẩn hóa request, context và prompt; `prompt_type`/`platform_name` được lưu ở message user và assistant. Với non-stream, `ask_ai()` chạy `output_validation_service.validate_and_sanitize()` trước khi lưu assistant. Với stream, chunk được gửi trực tiếp để hiển thị, sau đó ghép và lưu phần nội dung đã nhận; lỗi được biểu diễn bằng marker stream. Các message cũ vẫn dùng được nhờ nhánh tương thích legacy; không có migration xóa hoặc chuyển đổi dữ liệu cũ.

## 3.10. Luồng đầy đủ từ input người dùng đến output

Đây là luồng chuẩn cho một yêu cầu tạo hoặc chỉnh sửa nội dung quảng cáo. Dữ liệu người dùng được giữ ở phần user/context; không được đưa vào `system_instruction` để ghi đè quy tắc hệ thống.

```text
1. User nhập yêu cầu
   ├─ content: câu hỏi/yêu cầu chính
   ├─ prompt_type + platform_name: nền tảng/kênh đích
   ├─ ad_brief: sản phẩm, khách hàng, mục tiêu, tone, ngôn ngữ, độ dài...
   ├─ brand_id: thương hiệu được chọn (tùy chọn)
   └─ attachment_ids: file tham chiếu (tùy chọn)
             │
             ▼
2. Frontend tạo request
   ├─ lấy conversation_id hiện tại
   ├─ gửi JWT và payload qua POST /messages hoặc /messages/stream
   └─ nếu stream: chuẩn bị reader + AbortController
             │
             ▼
3. Message API xác thực và chuẩn hóa
   ├─ xác thực JWT, conversation và ownership
   ├─ trim/kiểm tra content không rỗng
   ├─ normalize prompt_type và kiểm tra nền tảng được hỗ trợ
   ├─ kiểm tra custom platform_name khi prompt_type = other
   ├─ kiểm tra brand/file thuộc user hiện tại
   └─ chuẩn hóa brief, platform và brand metadata
             │
             ▼
4. Lưu input trước khi gọi AI
   ├─ tạo Message(role=user, content, ad_brief_json, platform, brand)
   ├─ gắn attachment vào message và commit database
   └─ build_history() lấy lịch sử theo created_at
             │
             ▼
5. Dựng context gửi cho model
   ├─ giữ các message user/assistant cần thiết
   ├─ format brief vào user content
   ├─ đọc attachment hợp lệ: image/video/PDF bằng bytes,
   │  text/plain tối đa 50.000 ký tự
   ├─ nhận diện follow-up và lấy context brand/product
   └─ format role assistant → model theo Google Gen AI SDK
             │
             ▼
6. Dựng prompt và gọi provider
   ├─ build_system_prompt(): system rule an toàn
   ├─ ghép prompt chuyên biệt theo platform
   ├─ ghép platform intelligence, knowledge/trend context,
   │  ad brief rules và brand rules
   └─ gọi Gemini 2.5 Flash:
      ├─ generate_content() cho non-stream
      └─ generate_content_stream() cho stream
             │
             ├──────────────────────────────┐
             ▼                              ▼
7A. Non-stream                         7B. Stream
   nhận output hoàn chỉnh                nhận từng chunk
   → validate + sanitize                 → frontend ghép và hiển thị ngay
   → ghi learning dataset                → backend ghép full_response
   → lưu Message(role=assistant)         → lưu assistant nếu có nội dung
   → trả JSON cho frontend               → marker lỗi nếu provider gián đoạn
             │                              │
             └──────────────┬───────────────┘
                            ▼
8. Frontend nhận output cuối
   ├─ cập nhật bubble assistant
   ├─ hiển thị Markdown/nội dung đã tạo
   ├─ cho phép lưu library, đánh giá, tạo variant, campaign hoặc editor
   └─ cho phép gửi follow-up; request mới sẽ dùng lại history đã lưu
```

### Trạng thái dữ liệu qua pipeline

| Giai đoạn    | Dữ liệu chính                                                             | Nơi xử lý/lưu                             |
| ------------ | ------------------------------------------------------------------------- | ----------------------------------------- |
| Input        | `MessageCreate`, brief, platform, brand, attachment IDs                   | Frontend → `POST /messages*`              |
| Context      | `history[]`, brief đã serialize, attachment metadata/bytes, brand context | `message_service.py`, `ai_service.py`     |
| Prompt       | system instruction + platform prompt + context                            | `prompt_service.py`                       |
| Model output | text hoàn chỉnh hoặc từng chunk                                           | Gemini adapter trong `ai_service.py`      |
| Output cuối  | assistant content đã sanitize hoặc phần stream đã ghép                    | `messages` và response frontend           |
| Hậu xử lý    | learning record, saved content, evaluation/variant tùy thao tác tiếp theo | learning dataset và các service tương ứng |

### Điểm kết thúc và lỗi

- Lỗi input/ownership dừng trước khi gọi model và trả lỗi HTTP từ Message API.
- Lỗi provider ở non-stream được chuyển thành lỗi gateway; user message đã được lưu nhưng assistant response không được tạo thành công.
- Lỗi provider trong stream được gửi bằng `[ADGEN_QUOTA_ERROR]` hoặc `[ADGEN_STREAM_ERROR]`. Nếu đã có chunk, phần nội dung đó vẫn được lưu để không mất kết quả đã sinh.
- Với evaluation/variants, output đi qua nhánh structured: model trả JSON, backend parse bằng Pydantic rồi mới ghi activity và trả JSON cho frontend.

## 3.11. Các phương pháp xử lý và vị trí sử dụng LLM

Pipeline không đưa toàn bộ request trực tiếp cho LLM. Hệ thống kết hợp xử lý xác định (deterministic), context engineering, prompt engineering, multimodal processing, LLM inference và output validation. LLM chỉ được gọi sau khi request đã được xác thực và context đã được chuẩn bị.

```text
User input
    │
    ├─ [Deterministic] validate, normalize, ownership, lưu database
    │
    ├─ [Context engineering] history, brief, brand/product, attachment,
    │                       follow-up intent, context pruning
    │
    ├─ [Prompt engineering + grounding] system rules + platform prompt
    │                                  + knowledge/trend/brand context
    │
    ├─ [LLM inference] Gemini 2.5 Flash
    │       ├─ generate_content()          → non-stream text
    │       ├─ generate_content_stream()   → stream text
    │       └─ generate_content() + JSON   → evaluation/variants có cấu trúc
    │
    ├─ [Deterministic] validate/sanitize, kiểm tra claim và giới hạn platform
    │
    └─ [Persistence + delivery] lưu assistant/learning record → frontend
```

### Phân rã phương pháp theo từng đoạn

| Đoạn xử lý | Phương pháp | Có dùng LLM? | Thành phần chính |
| --- | --- | --- | --- |
| Nhận input | Schema validation, trim, normalize platform và custom platform | Không | `MessageCreate`, `message_service.py`, `prompt_service.py` |
| Bảo mật | JWT, ownership của conversation/brand/file | Không | Message API và service ownership checks |
| Chuẩn bị dữ liệu | Lưu user message, serialize brief, gắn attachment, load history | Không | `message_service.py` |
| Hiểu yêu cầu tiếp nối | Rule-based intent detection bằng regex/keyword; lấy platform, tone, số variant | Không trực tiếp | `FollowUpIntentResolver`, `ConversationContextService` |
| Quản lý context | Context pruning, lấy product context và assistant gần nhất, giới hạn lịch sử | Không trực tiếp | `context_engine` |
| Đa phương thức | Chuyển image/video/audio thành bytes và text/document thành text parts | Không trực tiếp; chuẩn bị dữ liệu cho model | `StandardMultimodalProcessor`, `format_history()` |
| Dựng instruction | Prompt engineering: system prompt, prompt theo platform, brief rules, brand rules | Không; đây là bước tạo instruction | `build_system_prompt()`, `backend/app/prompts/` |
| Grounding | Đưa platform intelligence, knowledge/trend context và dữ liệu brand/product vào context | Không tự truy xuất bằng LLM | `prompt_service.py`, brand/knowledge/trend services |
| Sinh nội dung | Text generation dựa trên toàn bộ `contents` và `system_instruction` | Có | Gemini 2.5 Flash trong `ai_service.py` |
| Sinh streaming | Gọi model và chuyển từng chunk về frontend | Có | `stream_ai()` → `generate_content_stream()` |
| Sinh structured | Yêu cầu JSON, parse schema bằng Pydantic cho evaluation/variants | Có | `generate_structured_content()`, `request_structured_ai()` |
| Kiểm tra output | Non-empty, forbidden claims, platform constraints, format repair | Không | `output_validation_service` |
| Trả và lưu kết quả | Ghép chunk, lưu assistant message, learning record, trả response | Không | `message_service.py`, frontend API |

### LLM được gọi ở đâu?

LLM text được gọi tại `backend/app/services/ai_service.py`, sau khi `message_service.py` đã xác thực request, lưu user message và tạo `history`:

1. `ask_ai()` gọi `client.models.generate_content()` cho non-stream. Model nhận `contents` gồm lịch sử đã format, brief và attachment parts; `system_instruction` được tạo bởi `build_system_prompt()`.
2. `stream_ai()` gọi `client.models.generate_content_stream()` cho chat stream. Model vẫn nhận cùng loại context, nhưng output được phát ra từng chunk.
3. `generate_structured_content()` gọi `generate_content()` với `response_mime_type="application/json"`; dùng cho các tác vụ cần schema như evaluation/variants, sau đó backend parse bằng Pydantic.

Vì vậy, LLM không chịu trách nhiệm cho các bước xác thực JWT, kiểm tra quyền, normalize field, nhận diện follow-up bằng regex, cắt ngắn context, lưu database hoặc kiểm tra policy đầu ra. Những bước này do backend thực hiện để kiểm soát dữ liệu và giảm rủi ro prompt injection/claim không có nguồn.

### Phân biệt LLM với các provider AI khác

| Tác vụ | Phương pháp/provider | Vai trò trong luồng |
| --- | --- | --- |
| Chat và copywriting | LLM Gemini 2.5 Flash | Hiểu context và sinh text/JSON |
| Image generation/edit | Gemini Image hoặc OpenAI Image adapter | Gọi riêng từ Media Studio, không đi qua `ask_ai()` |
| Video generation | Gemini Veo adapter | Submit → poll → download → validate → tạo `MediaAsset` |
| Voiceover | Edge TTS hoặc mock provider | Chuyển script đã làm sạch thành audio; đây là TTS, không phải LLM text generation |
| Output safety/format | Rule-based validator | Kiểm tra và sửa nhẹ output sau khi provider trả kết quả |

Trong luồng chat, LLM là bước sinh nội dung ở giữa pipeline; nó không thay thế các lớp kiểm soát trước và sau LLM. Với media, provider có thể là mô hình sinh ảnh/video riêng, còn voiceover dùng TTS adapter.

### Ví dụ theo một request thực tế

Với input: “Viết quảng cáo sản phẩm này cho TikTok, giọng trẻ trung, thêm CTA”:

1. Backend kiểm tra user, conversation, platform `tiktok` và brief.
2. `FollowUpIntentResolver` nhận diện `add_cta` nếu đây là yêu cầu tiếp nối; đây là rule-based, chưa gọi LLM.
3. Context engine lấy sản phẩm, brand và câu trả lời gần nhất; attachment được chuyển thành parts.
4. Prompt service ghép system rules, TikTok specification, brand rules và instruction thêm CTA.
5. Gemini 2.5 Flash sinh bản quảng cáo; đây là điểm LLM thực hiện suy luận và tạo nội dung.
6. Backend kiểm tra output không rỗng, claim bị cấm và giới hạn nền tảng, rồi stream hoặc trả nội dung hoàn chỉnh cho frontend.

## Bổ sung đồng bộ runtime

Luồng chat hiện giới hạn lịch sử còn khoảng sáu cặp user/assistant bằng `context_engine`, vẫn giữ brief/attachment/referential context và chèn yêu cầu follow-up hiện tại. `product_aware` tạo product/audience context khi brief trích xuất được; brand context và product context đi vào vùng reference data của user, không trộn trực tiếp vào system instruction. Gemini vẫn là bước LLM inference duy nhất của luồng text và được gọi qua API.

Non-stream và stream dùng cùng output validator và generation logging sau khi có kết quả hoàn chỉnh. Output rỗng hoặc ERROR/CRITICAL bị từ chối; WARNING được log nhưng không tự biến thành lỗi chặn. Stream lỗi trả marker lỗi, không lưu kết quả chưa hoàn tất; client hủy sau khi đã nhận một phần thì phần đã nhận được lưu để có thể khôi phục. Validator regex/heuristic chỉ kiểm tra cấu trúc/rủi ro, không bảo đảm claim đúng sự thật. Learning dataset là dữ liệu ghi nhận cho đánh giá/quy trình huấn luyện riêng, không phải cơ chế tự training/fine-tuning; trend registry không tự thu thập trend trực tuyến.