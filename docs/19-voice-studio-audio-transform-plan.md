# AdGen Voice Studio — Audio Transform Plan

| Trường | Giá trị |
|---|---|
| Plan | 18 |
| Name | Voice Studio Audio Transform |
| Status | DESIGN / NOT IMPLEMENTED |
| Created | 2026-10-06 |
| Scope | AdGen Voice Studio |
| Implementation | NOT STARTED |

## 1. Mục tiêu và phạm vi

Tài liệu này định hướng mở rộng AdGen Voice Studio theo hai trục độc lập:

1. Audio → Target Voice: lấy nội dung lời nói từ file audio rồi tạo audio mới bằng một giọng đích.
2. Text → User Voice: dùng file audio tham chiếu của người dùng để tạo audio từ văn bản mới.

Chức năng Text → TTS hiện tại phải tiếp tục hoạt động. Voice Studio được mở rộng trong cùng UI hiện có, không tạo một ứng dụng voice riêng.

Ở checkpoint này chỉ thiết kế và lập roadmap. Chưa triển khai upload audio, STT, voice conversion, voice cloning, provider mới, migration hoặc API mới.

## 2. Trạng thái hiện tại

Luồng hiện tại:

```text
AI message
→ Voice Studio
→ Script Cleaner / VoiceoverScriptExtractor
→ người dùng kiểm tra và chỉnh sửa text
→ chọn system voice
→ chọn tốc độ
→ tạo Voiceover
→ Audio Player
→ nghe hoặc tải audio
```

Voice Studio hiện có Text → Voice với các voice như Hoài My, Nam Minh và các voice khác nếu provider cung cấp. Provider hiện tại không được mặc định xem là hỗ trợ voice conversion, voice cloning hoặc custom voice. Khả năng thực tế phải được audit trước khi triển khai.

Các thành phần hiện có cần được tái sử dụng khi phù hợp:

- `frontend/src/components/chat/VoiceoverModal/VoiceoverModal.jsx`
- `frontend/src/components/chat/VoiceoverModal/AudioPlayer.jsx`
- `frontend/src/services/api/voiceoverApi.js`
- `backend/app/api/voiceover.py`
- `backend/app/services/voiceover/voiceover_service.py`
- `backend/app/services/voiceover/extractor.py`
- `backend/app/services/voiceover/providers/`
- `backend/app/models/voiceover_audio.py`

## 3. Mô hình nguồn độc lập

Voice Studio cần phân biệt hai khái niệm:

### Content Source

- Filtered Text: văn bản đã được Script Cleaner lọc và người dùng có thể chỉnh sửa.
- Audio Content: nội dung lời nói được trích xuất từ file audio bằng STT hoặc cơ chế phù hợp.

### Voice Source

- System Voice: voice có sẵn của provider, ví dụ Hoài My hoặc Nam Minh.
- User Voice Reference: file audio được người dùng chọn làm tham chiếu giọng.

Content Source và Voice Source là hai lựa chọn độc lập. Khi có cả Text và Audio, UI không được tự mặc định Audio luôn thắng Text. Audio có thể là nguồn nội dung hoặc chỉ là voice reference; người dùng phải kiểm soát semantics này.

## 4. Các use case mục tiêu

### Case A — Existing Text → System Voice

```text
Filtered Text + System Voice
→ Generated Audio
```

Đây là luồng hiện tại, phải giữ nguyên hành vi và tương thích ngược.

### Case B — Audio → Target Voice

```text
User Audio
→ lấy nội dung lời nói
→ Target Voice
→ Generated Audio
```

Phase triển khai phải xác định rõ đây là true voice conversion hoặc STT → TTS pipeline. Không gọi là voice conversion nếu thực tế chỉ có STT rồi tổng hợp bằng TTS. Cần mô tả trade-off về timing, phát âm, cảm xúc, speaker identity, chất lượng và latency.

### Case C — Filtered Text → User Voice

```text
User Voice Reference + Filtered Text
→ Generated Audio bằng voice tham chiếu
```

Ví dụ người dùng chọn `my_voice.wav` làm voice reference, nhưng nội dung mới là một đoạn quảng cáo khác. Hệ thống phải giữ text mới và chỉ dùng audio làm nguồn giọng.

Provider phải thực sự hỗ trợ speaker-conditioned TTS, custom voice, voice cloning hoặc capability tương đương mới được triển khai. Không được suy luận capability này từ việc provider hiện tại có TTS.

## 5. UX direction

Giữ nguyên Voice Studio hiện tại và mở rộng form theo từng nhóm rõ ràng:

### Nguồn nội dung

- Văn bản đã lọc
- File âm thanh

### Nguồn giọng

- Voice có sẵn
- Giọng từ file của tôi

Tái sử dụng textarea, voice selector, speed control nếu provider hỗ trợ, Audio Player, download, loading, retry và error state hiện có.

Khi chỉ có một nguồn đầu vào, hệ thống có thể chọn mặc định. Khi có cả Text và Audio, phải hiển thị rõ Audio đang được dùng làm Content Source hay Voice Source. Không được hard-code priority theo loại file.

UI không được cho phép người dùng chọn một capability mà backend/provider chưa xác nhận. Trạng thái capability nên được trả qua abstraction của provider thay vì gắn cứng tên provider vào frontend.

## 6. Roadmap theo phase

### Phase 0 — Audit & Feasibility

Chưa code. Audit:

- ChatInput và các loại file đang hỗ trợ.
- Upload/storage và `MediaAsset` hoặc model tương đương.
- Audio MIME, format, size và duration validation.
- STT hiện có hay chưa.
- Voiceover service và Script Cleaner hiện tại.
- Voice provider, provider adapter và cách cung cấp các system voice.
- Provider có hỗ trợ speech-to-text, voice conversion, voice cloning, speaker reference, custom voice hoặc voice-conditioned TTS hay không.
- Giới hạn format, thời lượng, kích thước, chi phí và API limitation.
- Storage lifecycle, retention, cleanup và ownership.
- Khả năng tái sử dụng code hiện có.

Phase 0 kết thúc bằng feasibility decision cho từng use case. Không code khi chưa có kết luận provider.

### Phase 1 — Audio Input Foundation

Chỉ triển khai nếu Phase 0 xác nhận khả thi:

- upload audio;
- MIME/format validation;
- size/duration validation;
- storage và ownership;
- preview;
- delete/cleanup;
- API contract và tests.

Không triển khai voice conversion trong phase này nếu chưa cần cho foundation.

### Phase 2 — Voice Studio UI Extension

Mở rộng UI hiện tại với Content Source và Voice Source. Tách rõ state của text, audio content, system voice và user voice reference. Không tạo component/application trùng lặp.

### Phase 3 — Audio → Target Voice

Triển khai theo capability đã được xác nhận ở Phase 0. Ghi rõ pipeline thực tế là voice conversion hay STT → TTS, cùng giới hạn về timing, pronunciation, emotion, identity, quality và latency.

### Phase 4 — Filtered Text → User Voice

Triển khai use case quan trọng này chỉ khi provider có capability phù hợp. Phân biệt chính xác voice cloning, speaker-conditioned TTS, custom voice và voice conversion. Bổ sung consent/safety cho voice reference.

### Phase 5 — Integration, Persistence & History

Hoàn thiện:

- generated audio persistence và metadata;
- source traceability;
- ownership và protected access;
- history, preview và download;
- cleanup, retention và retry;
- error states;
- API/frontend contract;
- regression tests.

Không cascade-delete artifact quan trọng nếu chưa có policy rõ ràng.

## 7. Data/API design direction

Đây chỉ là hướng thiết kế, chưa chốt tên model/table trước Phase 0.

Các abstraction cần đánh giá:

- reuse `AudioAsset`/`MediaAsset`;
- `VoiceReference`;
- `VoiceTransformationJob` hoặc abstraction tương đương;
- `GeneratedVoiceAsset`.

Metadata có thể cần:

- `source_audio_id`;
- `content_source`;
- `voice_source`;
- `target_voice`;
- provider/model;
- status/error;
- duration;
- owner user;
- created/updated timestamps.

API cần biểu diễn rõ source selection, capability, processing state, output metadata và ownership. Không đưa provider-specific behavior trực tiếp vào UI khi có thể dùng provider abstraction.

## 8. Security và privacy

Thiết kế phải bao gồm:

- owner isolation cho audio, voice reference và generated audio;
- không cho user dùng voice reference của user khác;
- file/MIME/type validation;
- size/duration limits;
- không expose raw storage path;
- protected playback/download;
- cleanup và retention policy;
- consent khi dùng voice reference;
- không lưu hoặc sử dụng voice reference ngoài workflow người dùng đã chọn;
- không cho phép autonomous voice generation ngoài hành động rõ ràng của người dùng.

Voice reference phải có lifecycle và policy riêng. Không mặc định chia sẻ public, không tự động clone giọng người khác và không dùng một file audio cho cả Content Source lẫn Voice Source nếu người dùng chưa xác nhận semantics.

## 9. Testing strategy

### Backend

- upload và file validation;
- ownership/cross-user isolation;
- provider abstraction và capability reporting;
- job lifecycle;
- success/failure/retry;
- idempotency nếu cần;
- invalid provider response;
- content source và voice source selection;
- existing Text → System Voice regression.

### Frontend

- chuyển Content Source;
- chuyển Voice Source;
- upload/loading/preview;
- generation state;
- error và retry;
- source combination hợp lệ/không hợp lệ;
- existing Voice Studio regression;
- không hiển thị capability chưa được backend xác nhận.

### Integration

- Text → system voice;
- Audio → target voice;
- Filtered Text → user voice;
- thiếu hoặc xung đột nguồn;
- ownership isolation;
- persistence, history và protected audio access.

## 10. Architecture principles

1. Không phá Text → Voice hiện tại.
2. Content Source và Voice Source là hai khái niệm độc lập.
3. Không mặc định Audio luôn có priority cao hơn Text.
4. Khi Text và Audio cùng tồn tại, semantics phải do người dùng chọn hoặc được xác định bởi contract rõ ràng.
5. Provider capability phải được audit trước implementation.
6. Không hard-code provider-specific behavior vào UI.
7. Dùng provider interface/adapter nếu có nhiều provider.
8. Không dùng LLM để quyết định mơ hồ nguồn nội dung nếu user selection có thể xác định rõ.
9. Audio generation phải có ownership và protected access.
10. Voice reference chỉ được sử dụng đúng mục đích người dùng đã chọn.
11. Không tạo audio tự động ngoài user action.
12. Feature mới không được làm thay đổi flow hiện tại khi người dùng không sử dụng feature đó.

## 11. Non-goals

Plan này không bao gồm:

- social voice marketplace;
- public sharing voice reference;
- tự động clone giọng người khác;
- real-time voice conversion;
- live microphone transformation;
- podcast/meeting transcription tổng quát;
- thay thế toàn bộ Voice Studio hiện tại;
- autonomous agent chỉ để tạo voice.

## Current Status

- Plan created.
- Existing Text → TTS Voice Studio improvements are complete: deterministic marker extraction, controlled no-marker fallback, shared clean/generate extraction contract, original/cleaned text toggle, light/dark theme compatibility and simplified mic icons.
- The Audio Transform implementation described by this plan has not started.
- Phase 0 audit pending.
- Provider capability chưa được xác minh cho voice conversion, STT, voice cloning, custom voice hoặc speaker-conditioned TTS.
- No backend/frontend/database/provider changes in this checkpoint.
- No commit/push.
