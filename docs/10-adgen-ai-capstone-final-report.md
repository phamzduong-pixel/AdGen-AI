# AdGen AI — Capstone Project Final Report

> Mẫu tham chiếu: `main.pdf` — Samsung Innovation Campus, AI Course, Capstone Project Final Report
> Ngày cập nhật: 09/10/2026
> Trạng thái: Báo cáo được điền theo source code, tài liệu và kết quả kiểm thử hiện có; các runtime/provider chưa xác minh được ghi rõ.

## Thông tin dự án

| Trường | Thông tin |
| --- | --- |
| Project Title | AdGen AI — Marketing Assistant and Voice Studio |
| Course | AI Course — Samsung Innovation Campus |
| Class | SIC-AI-N02 |
| Instructor | TS. Trần Quang Quý |
| Team Name | AdGen AI |
| Members | Chưa cung cấp danh sách thành viên chính thức |
| Repository | `C:\Users\MY PC\Documents\AI\AdGenAI` |

> Tài liệu này không thay thế mẫu PDF gốc. Những mục cần chữ ký, ảnh nhóm, tên thành viên hoặc nhận xét giảng viên vẫn cần bổ sung thủ công.

## List of Abbreviations

| Abbreviation | Full definition / description |
| --- | --- |
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| E2E | End-to-end |
| EDA | Exploratory Data Analysis |
| FFmpeg | Công cụ xử lý/chuyển đổi media |
| FFprobe | Công cụ đọc metadata và kiểm tra media |
| JWT | JSON Web Token |
| STT | Speech-to-Text |
| TTS | Text-to-Speech |
| UI | User Interface |
| Vosk | Local/offline Speech-to-Text provider |
| VC | Voice Conversion |

## 1. Introduction

### 1.1. Background Information

AdGen AI là nền tảng hỗ trợ tạo, chỉnh sửa, đánh giá và quản lý nội dung quảng cáo bằng AI. Hệ thống cung cấp Chat, brief, brand context, template, campaign, thư viện nội dung, Media Studio và Voice Studio trên cùng một ứng dụng web.

Voice Studio là module chuyển nội dung quảng cáo thành audio. Luồng ban đầu là **Text → Edge TTS**. Plan 18 mở rộng module để người dùng có thể chọn nội dung từ văn bản hoặc file audio/video, nhận dạng lời thoại, chỉnh sửa transcript và tạo audio bằng giọng có sẵn hoặc reference voice khi provider local sẵn sàng.

### 1.2. Motivation and Objective

Mục tiêu của dự án là giảm thời gian chuẩn bị nội dung quảng cáo và tạo voiceover, đồng thời giữ rõ ranh giới giữa:

- nội dung cần đọc;
- nguồn giọng dùng để tổng hợp;
- nhận dạng lời nói;
- text-to-speech;
- reference-voice TTS;
- Direct Voice Conversion.

Mục tiêu kỹ thuật của Plan 18:

1. Giữ ổn định Text → Edge TTS hiện có.
2. Hỗ trợ Audio/Video → STT → Text Review/Edit → Edge TTS.
3. Cung cấp nền tảng reference voice local bằng VieNeu-TTS khi môi trường riêng sẵn sàng.
4. Fail-closed khi provider, model, codec, authentication hoặc runtime prerequisite chưa có.
5. Không tạo transcript/audio giả và không nhầm STT → TTS với Voice Conversion.

### 1.3. Members and Role Assignments

Danh sách tên thành viên chưa được cung cấp trong repository. Bảng dưới đây là phân công vai trò dự kiến, chưa phải danh sách nhân sự chính thức.

| No. | Member name | Assigned role |
| --- | --- | --- |
| 1 | Chưa cung cấp | Project coordination and system architecture |
| 2 | Chưa cung cấp | Backend API, STT and media validation |
| 3 | Chưa cung cấp | Frontend Voice Studio and responsive UI |
| 4 | Chưa cung cấp | Provider/runtime verification and testing |
| 5 | Chưa cung cấp | Documentation, deployment and operations |

### 1.4. Schedule and Milestones

| Phase | Checkpoints / work | Status |
| --- | --- | --- |
| 1 | Text → Edge TTS, script extraction and Voice Studio baseline | Completed; real Edge TTS was previously verified in a controlled short test |
| 2 | STT audit, audio/video validation and Video → STT foundation | Implemented foundation; real authenticated provider runtime remains environment-dependent |
| 3 | Local Vosk setup and provider integration | Adapter/factory/tests exist; runtime quality and authenticated E2E still require verification |
| 4 | Voice Studio unified file input and responsive UI | Implemented and frontend checks passed |
| 5 | VieNeu-TTS reference-voice foundation | Implemented worker/provider contract; model/runtime readiness is conditional |
| 6 | Direct Voice Conversion | Seed-VC CPU integration implemented; real runtime remains fail-closed until external environment/model/reference assets are complete |
| 7 | Final runtime verification and production hardening | Pending separate controlled verification |

## 2. Project Execution

### 2.1. Data Acquisition

AdGen AI nhận dữ liệu từ:

- prompt, brief, brand context và lịch sử hội thoại do người dùng cung cấp;
- nội dung văn bản dùng để tạo voiceover;
- file audio/video người dùng chọn để nhận dạng lời thoại hoặc làm reference voice;
- fixture media local được phép sử dụng cho unit/integration testing.

File audio/video được kiểm tra loại, MIME/signature, codec/container, kích thước, duration và audio stream trước khi đưa vào STT hoặc reference-voice pipeline. File tạm được xử lý trong thư mục tạm và cleanup khi request kết thúc.

Không có bằng chứng cho thấy repository đang huấn luyện lại một mô hình AI từ đầu. `backend/app/data/learning_dataset.jsonl` là dữ liệu/log phục vụ learning feedback và phân tích; nó không phải model weights và không chứng minh hệ thống đã fine-tune một model riêng.

### 2.2. Training Methodology

Hệ thống hiện không dùng quy trình supervised training nội bộ để tạo model text, STT hoặc TTS. Phương pháp chính là:

1. **Prompt/context engineering:** ghép system prompt, platform prompt, brief, brand context và lịch sử hội thoại.
2. **Provider abstraction:** gọi provider qua service/adapter; giữ mock provider cho test offline.
3. **Structured validation:** kiểm tra schema, field bắt buộc, kích thước, duration, codec, timeout và output trước khi trả về.
4. **Deterministic script extraction:** nhận diện marker thoại, fallback heuristic có kiểm soát và giữ nguyên nội dung được chọn.
5. **Local pretrained inference:** Vosk và VieNeu-TTS, nếu được cấu hình, dùng model pretrained local; không tự tải model trong request và không tự động huấn luyện lại model.

### 2.3. Workflow

#### Text source

```text
AI response / user text
  → Voice Studio
  → extract or review dialogue
  → choose built-in voice
  → Edge TTS
  → validate audio output
  → playback / download
```

#### Audio source

```text
Audio upload
  → size/MIME/signature/codec/duration validation
  → POST /stt/transcribe
  → transcript review/edit
  → choose voice
  → Edge TTS or configured reference-voice provider
  → playback / download
```

#### Video source

```text
Video upload
  → video validation and audio-stream check
  → FFmpeg extraction
  → extracted-audio validation
  → POST /stt/transcribe-video pipeline
  → transcript review/edit
  → Edge TTS
  → playback / download
```

#### Reference voice

```text
Text + reference audio/video
  → reference validation
  → video audio extraction when needed
  → PCM mono 16 kHz conversion
  → VieNeu-TTS worker in separate CPU/ONNX environment
  → output validation and MP3 conversion
  → playback / download
```

### 2.4. System Design

```text
React/Vite frontend
  ├─ VoiceoverModal
  ├─ Content Source: text / file
  ├─ Voice Source: built-in / reference
  ├─ transcript editing and media preview
  └─ API clients
          │ authenticated JSON/multipart requests
          ▼
FastAPI backend
  ├─ /voiceover/clean-script
  ├─ /voiceover/generate
  ├─ /voiceover/generate-reference
  ├─ /stt/transcribe
  ├─ /stt/transcribe-video
  ├─ /voice-conversion/convert
  ├─ /voice-conversion/convert-reference
  └─ /voice-conversion/convert-reference-video
          │
          ├─ Edge TTS provider
          ├─ STT factory → Vosk / Google adapter / Unavailable provider
          ├─ FFmpeg/FFprobe validation and extraction
          ├─ VieNeu-TTS worker via separate Python environment
          ├─ Seed-VC CPU subprocess adapter and preset/custom references
          └─ local temporary/output storage
```

Authentication, ownership checks, stable error codes, bounded subprocesses, timeout handling and cleanup are part of the backend contract. Provider capability is not inferred from a UI button alone.

## 3. Results

### 3.1. Data Preprocessing

Đã có các bước preprocessing chính:

- làm sạch/trích xuất lời thoại từ script bằng `VoiceoverScriptExtractor`;
- giữ riêng text gốc và text đã lọc;
- validate file upload trước khi STT;
- dùng FFprobe để kiểm tra metadata media;
- dùng FFmpeg để trích xuất audio/video và chuẩn hóa PCM khi pipeline cần;
- kiểm tra file output không rỗng, duration hợp lệ và cleanup temporary files;
- chống stale response khi người dùng đổi file, đổi tab hoặc đóng modal trong lúc request chạy.

### 3.2. Exploratory Data Analysis

EDA theo nghĩa dataset training không áp dụng cho implementation hiện tại, vì AdGen AI chưa huấn luyện model riêng trong repository. Các kiểm tra tương đương ở runtime là:

- kiểm tra format/container/codec/duration/audio stream;
- kiểm tra transcript rỗng hoặc malformed;
- kiểm tra output audio và error mapping;
- kiểm tra resource safety, timeout và cleanup.

Nếu dự án cần báo cáo chất lượng STT định lượng, cần bổ sung bộ audio tiếng Việt có consent, transcript chuẩn và phép đo WER/CER riêng.

### 3.3. Modeling and Provider Evaluation

| Capability | Current result | Evidence / limitation |
| --- | --- | --- |
| Text → Edge TTS | Implemented; previous short real runtime succeeded | Không đồng nghĩa mọi deployment/provider đều đã PASS |
| Vosk local STT | Adapter/factory/config/test foundation implemented | Model load đã có bằng chứng trong benchmark setup; E2E/authenticated quality trên mọi file chưa xác minh |
| Google Cloud STT | Adapter tồn tại nhưng không phải provider mặc định | Không gọi API thật trong các checkpoint audit |
| VieNeu-TTS reference voice | Separate worker/provider foundation implemented | Phụ thuộc Python worker, model/codec cache, RAM/CPU và file reference có quyền sử dụng |
| Direct Voice Conversion | Source/API/UI integration implemented | Chạy Seed-VC CPU khi `VC_PROVIDER=seed-vc`; runtime thật chưa PASS do thiếu external environment/model/reference đầy đủ |

### 3.4. User Interface

Voice Studio hiện có:

- hai tab Content Source: **Văn bản quảng cáo** và **File giọng nói**;
- preview audio/video, thay file, xóa file và giới hạn hiển thị phù hợp mobile/desktop;
- nút **Nhận dạng lời thoại** chỉ nhận dạng và điền transcript;
- vùng transcript có thể chỉnh sửa trước khi tạo audio;
- hai Voice Source: **Giọng có sẵn** và **Giọng tham chiếu của tôi**;
- loading/error state, cleanup object URL và bảo vệ stale response;
- nhãn sản phẩm hiển thị theo thương hiệu **AdGen AI**, không dùng Gemini làm tên sản phẩm;
- layout light/dark và responsive compact.

### 3.5. Testing and Improvements

Bằng chứng kiểm tra frontend gần nhất:

- `npm test`: **68/68 pass**;
- `npm run lint`: **PASS**;
- `npm run build`: **PASS**;
- `git diff --check`: **PASS**; cảnh báo LF/CRLF là line-ending warning của working tree.

Backend có targeted suites cho audio probe, STT API/service, Google adapter, Vosk, video-to-STT, reference voice và voice conversion. Full suite gần nhất: **495 tests PASS** và 74 subtests PASS; OpenAPI 97 paths, health, CORS local, migration head, compileall và dependency integrity PASS. Mock/unit tests không thay thế runtime provider thật.

## 4. Projected Impact

### 4.1. Accomplishments and Benefits

- Một UI duy nhất cho nội dung text, audio và video.
- Người dùng có thể review/edit transcript trước khi tạo audio.
- Giữ nguyên luồng Text → Edge TTS đang hoạt động.
- Xử lý STT local-first có thể bảo vệ dữ liệu audio nếu model được provision local.
- Validation, timeout và cleanup giảm rủi ro file giả, file hỏng và resource exhaustion.
- Tách Content Source khỏi Voice Source giúp không nhầm file nội dung với file tham chiếu giọng.
- Kiến trúc provider cho phép giữ fail-closed khi provider/model chưa sẵn sàng.

### 4.2. Future Improvements

1. Hoàn tất authenticated runtime verification cho Audio → Vosk STT → Edge TTS.
2. Kiểm tra riêng Video → FFmpeg → Vosk STT → Edge TTS bằng fixture có consent.
3. Benchmark VieNeu-TTS trên phần cứng triển khai với giới hạn RAM/CPU thực tế.
4. Bổ sung WER/CER và đánh giá thủ công chất lượng tiếng Việt với transcript chuẩn.
5. Provision Python 3.10/checkpoint Seed-VC, cấu hình `SEED_VC_PYTHON`/`SEED_VC_DIR`, bổ sung reference WAV còn thiếu và chạy authenticated CPU E2E trước khi công bố runtime PASS.
6. Hoàn thiện persistent storage/retention policy cho deployment production.
7. Bổ sung tên thành viên, ảnh nhóm, nhận xét cá nhân và đánh giá giảng viên vào bản nộp chính thức.

## 5. Team Member Review and Comment

Chưa có thông tin thành viên chính thức để điền vào mục này. Bảng giữ nguyên để bổ sung sau:

| Member name | Review and comment |
| --- | --- |
| Chưa cung cấp | Chưa cung cấp |
| Chưa cung cấp | Chưa cung cấp |
| Chưa cung cấp | Chưa cung cấp |
| Chưa cung cấp | Chưa cung cấp |
| Chưa cung cấp | Chưa cung cấp |

## 6. Instructor Review and Comment

| Category | Score | Review and comment |
| --- | --- | --- |
| IDEA | Chưa đánh giá | Chưa cung cấp |
| APPLICATION | Chưa đánh giá | Chưa cung cấp |
| RESULT | Chưa đánh giá | Chưa cung cấp |
| PROJECT MANAGEMENT | Chưa đánh giá | Chưa cung cấp |
| PRESENTATION & REPORT | Chưa đánh giá | Chưa cung cấp |
| TOTAL | Chưa đánh giá | Chưa cung cấp |

Instructor signature: Chưa cung cấp  
Date: Chưa cung cấp

## References

1. `docs/09-voice-studio-audio-transform-plan.md` — Plan 18 Voice Studio Audio Transform.
2. `docs/00-tong-quan-he-thong.md` — system overview and current implementation status.
3. `docs/07-huong-dan-su-dung-he-thong.md` — user guide and Voice Studio workflow.
8. `backend/app/api/voiceover.py`, `backend/app/api/stt.py`, `backend/app/api/video_stt.py`, `backend/app/api/voice_conversion.py`.
9. `backend/app/services/voiceover/`, `backend/app/services/stt/`, `backend/app/services/voice_studio/`, `backend/app/services/voice_conversion/`.
10. VieNeu-TTS upstream: <https://github.com/pnnbao97/VieNeu-TTS>.
11. Vosk upstream/model list: <https://alphacephei.com/vosk/models>.

## Appendix A. Source Code and Implementation Details

### A.1. Frontend

- `frontend/src/components/chat/VoiceoverModal/VoiceoverModal.jsx`
- `frontend/src/components/chat/VoiceoverModal/VoiceoverModal.css`
- `frontend/src/components/chat/VoiceoverModal/audioInput.js`
- `frontend/src/components/chat/VoiceoverModal/videoInput.js`
- `frontend/src/components/chat/VoiceoverModal/fileInput.js`
- `frontend/src/services/api/voiceoverApi.js`
- `frontend/tests/voiceoverModalContract.test.js`
- `frontend/tests/voiceoverAudioInput.test.js`
- `frontend/tests/voiceoverVideoInput.test.js`

### A.2. Backend

- `backend/app/api/voiceover.py`
- `backend/app/api/stt.py`
- `backend/app/api/video_stt.py`
- `backend/app/api/voice_conversion.py`
- `backend/app/services/stt/providers/factory.py`
- `backend/app/services/stt/providers/vosk.py`
- `backend/app/services/voice_studio/video_to_stt.py`
- `backend/app/services/voice_studio/video_input.py`
- `backend/app/services/voice_conversion/audio_probe.py`
- `backend/app/services/voiceover/providers/vieneu_reference_provider.py`
- `backend/app/services/voiceover/providers/vieneu_worker.py`
- `backend/app/core/config.py`

### A.3. Runtime safety contract

- Không đọc hoặc in secret/API key.
- Không tự tải model trong request runtime.
- Không gửi audio reference ra ngoài local worker khi dùng VieNeu-TTS.
- Gọi subprocess với `shell=False`, timeout và output bound.
- Cleanup uploaded media/extracted audio/reference temp files ở success và failure.
- Không gọi provider sau khi validation hoặc extraction thất bại.
- Không coi mock transcript/audio là runtime evidence.

## Appendix B. Runtime Configuration

| Configuration | Current contract |
| --- | --- |
| `STT_PROVIDER` | `vosk`, `google-cloud` hoặc rỗng để fail-closed |
| `STT_DEFAULT_LANGUAGE` | `vi-VN` mặc định |
| `STT_AUDIO_MAX_SIZE` | 10 MB mặc định |
| `STT_AUDIO_MAX_DURATION_SECONDS` | Đọc từ cấu hình runtime; phải kiểm tra theo deployment hiện tại |
| `STT_PROVIDER_TIMEOUT_SECONDS` | Timeout provider STT |
| `VOSK_MODEL_PATH` | Đường dẫn model local; mặc định Windows nằm ngoài repository |
| `VC_PROVIDER` | `disabled` mặc định; đặt `seed-vc` để bật integration đã triển khai |
| `SEED_VC_PYTHON` | Python 3.10 của môi trường Seed-VC tách biệt |
| `SEED_VC_DIR` | Checkout Seed-VC chứa `inference.py` |
| `SEED_VC_DIFFUSION_STEPS` | Số bước diffusion; mặc định 20 |
| `VIENEU_PYTHON` | Python worker VieNeu-TTS riêng |
| `VIENEU_CACHE_DIR` | Cache model/codec VieNeu-TTS riêng |
| `VIENEU_REFERENCE_MAX_SIZE_BYTES` | 10 MB mặc định |
| `VIENEU_REFERENCE_MAX_DURATION_SECONDS` | 60 giây mặc định |
| `FFMPEG_BINARY` / `FFPROBE_BINARY` | Binary xử lý/probe media |

> Không ghi giá trị secret vào báo cáo. Các biến cần secret như `SECRET_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, SMTP credentials và Google credentials chỉ được cấu hình ngoài repository.

## Completion Status

**PARTIAL — REPORT FILLED FROM CURRENT SOURCE AND TEST EVIDENCE**

Bản báo cáo đã điền theo cấu trúc của `main.pdf`, nhưng chưa thể đánh dấu production-ready vì authenticated runtime STT/video, VieNeu-TTS runtime ổn định và Seed-VC inference thật vẫn chưa được xác minh đầy đủ. Seed-VC đã có integration source/API/UI; điều còn thiếu là external runtime/model/reference assets và bằng chứng CPU E2E. Không có kết luận rằng hệ thống đã huấn luyện model riêng chỉ từ sự tồn tại của learning dataset hoặc provider package. Không có kết luận rằng hệ thống đã huấn luyện model riêng chỉ từ sự tồn tại của learning dataset hoặc provider package.

## Addendum — Chat lifecycle audit (11/10/2026)

Audit CP-1 đến CP-12 xác minh commit user trước retrieval, validation evidence, canonical final content và edit consistency bằng source/test offline. Chưa có bằng chứng cho full backend discovery, FFmpeg/FFprobe/provider integration thật hoặc remote provider cancellation; các mục này không được coi là PASS.
