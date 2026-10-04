# 15. Runtime hardening và quy trình bàn giao

## Database mới và database đã có dữ liệu

Có hai đường đi riêng, không được dùng lẫn:

- Database hoàn toàn rỗng, disposable: sau khi cấu hình `DATABASE_URL`, chạy `python -m app.database.bootstrap --confirm-empty` hoặc `python -m app.database.prepare_database`. Bootstrap tạo schema từ metadata hiện tại, validate manifest/model/index, rồi mới ghi marker Alembic `20261003_0017`. Lệnh này từ chối mọi database không chứng minh được là `EMPTY_UNMANAGED`.
- Database đã có dữ liệu và đang ở revision hợp lệ: backup trước, sau đó chạy `alembic upgrade head` để áp dụng migration `20261003_0017_voiceover_audio_ownership`. Nếu schema lệch, legacy hoặc không rõ lịch sử, runtime fail-closed; dùng `python -m app.database.legacy_reconciliation` để kiểm tra chỉ đọc và lập kế hoạch migration riêng.

Không sửa migration đã phát hành `20260727_0001`/`0008`, không stamp marker để che mismatch, không drop table và không xóa database. Lỗi index campaign primary của chuỗi lịch sử cũ được tránh cho database rỗng bằng bootstrap đã validate; chuỗi migration cũ vẫn phải được xử lý có kiểm soát cho database đã phát hành.

Backend Docker chạy `prepare_database` trước Uvicorn. Vì vậy container chỉ khởi động khi database rỗng đã được bootstrap an toàn hoặc database hiện hữu đã đúng canonical schema. Docker Compose dùng PostgreSQL volume; Render dùng PostgreSQL managed và backend Docker. Frontend build dùng `npm ci` từ lockfile hiện hành.

## Voice Studio

`POST /voiceover/generate` và `GET/HEAD /voiceover/audio/{filename}` đều yêu cầu JWT. Bản ghi `voiceover_audios` lưu chủ sở hữu và endpoint chỉ trả file khi user hiện tại sở hữu bản ghi. File legacy không có owner không được tự gán và trả 404. Frontend tải audio bằng Axios với Authorization header, tạo Blob URL tạm cho playback/download; JWT không nằm trong URL.

## AI provider, dataset và trend

Gemini được gọi qua API; test tự động dùng mock và không gửi request trả phí. `learning_dataset.jsonl` là dữ liệu ghi nhận để đánh giá/quan sát và có thể làm đầu vào cho một quy trình huấn luyện riêng, không có nghĩa hệ thống tự fine-tune hoặc tự huấn luyện model. Trend registry chỉ cung cấp trend đã đăng ký/xác minh trong hệ thống, không tự thu thập trend trực tuyến.

WARNING từ output validator được log và vẫn cho phép trả kết quả nếu không có lỗi chặn; ERROR/CRITICAL và output rỗng bị từ chối. Regex/heuristic validator chỉ là lớp kiểm tra định dạng và rủi ro, không bảo đảm mọi claim trong nội dung là đúng sự thật.

## Cách xác minh

```powershell
cd backend
python -m pytest -q tests/test_voiceover_api.py tests/test_database_bootstrap.py
python -m pytest -q tests/test_conversation_management.py tests/test_brands.py tests/test_output_validator.py
python -m smoke.voiceover_extraction_smoke
python -m smoke.voiceover_flow_smoke

cd ..\frontend
npx --yes npm@10.9.2 ci
npm test
npm run lint
npm run build
```

Các kết quả trên là implementation/unit/mock và SQLite disposable. Không coi chúng là xác minh provider Gemini/TTS thật, FFmpeg thật hoặc PostgreSQL production. Chỉ chạy smoke provider thật khi đã có quyền truy cập, quota và phê duyệt chi phí riêng.
## Cập nhật giao diện và nhận diện logo — 04/10/2026

Đã hoàn tất đồng bộ logo thương hiệu và màu giao diện nội bộ:

1. `--brand-mark-bg`, `--brand-mark-fg`, `--brand-mark-border` và `--brand-mark-shadow` là nguồn màu dùng chung trong `frontend/src/styles/variables.css`.
2. Logo DG ở Sidebar, Login/Register, Recovery và Workspace dùng cùng kiểu badge bo góc; Chat Empty State dùng cùng màu cho biểu tượng thương hiệu.
3. Light mode dùng `#eef2ff` + `#4f46e5`; dark/system dark dùng `#1e1b4b` + `#a5b4fc`.
4. Header Chat không còn render biểu tượng tia sét; avatar người dùng không bị thay đổi vì không phải logo thương hiệu.
5. Nền hội thoại, vùng footer và composer Chat dark đã được đưa về cùng canvas; composer chỉ giữ độ nổi nhẹ bằng màu surface.

Kiểm thử thực tế sau cập nhật: `npm run lint` PASS, `npm test` PASS (38/38), `npm run build` PASS và `git diff --check` PASS. Đây là bằng chứng implementation/unit/build; visual QA đa trình duyệt vẫn cần thực hiện khi có môi trường trình duyệt mục tiêu.
## Cap nhat giao dien va dark mode — 05/10/2026

Da hoan tat tinh chinh giao dien React/Vite:

- Nhom nut tao hoi thoai moi (`New Chat` va `Cuoc tro chuyen moi`) dung gradient pastel xanh-indigo/tim nhat hon, chu va trang thai hover van dam bao do tuong phan.
- Bo duong ke ngang ro mau xanh duoi header Chat; header dung nen pha tron nhe va khong con border hien ro.
- Dong bo mau dark mode cho nen chinh, sidebar, header, card, modal, input, text phu, border va hover theo cung he token indigo.
- Giu rieng xu ly light/dark de khong lam thay doi hanh vi chuc nang hoac API.
- Cac file style chinh: `frontend/src/styles/globals.css`, `frontend/src/components/chat/Header/Header.css`, `frontend/src/components/chat/Header/HeaderActions/HeaderActions.css`, `frontend/src/components/chat/Sidebar/SidebarHeader/SidebarHeader.css` va `frontend/src/layouts/ChatLayout/ChatLayout.css`.

Kiem tra sau cap nhat: `npm run lint` PASS, `npm test` PASS (38/38), `npm run build` PASS va `git diff --check` PASS. Visual QA tren trinh duyet muc tieu van la buoc bo sung neu can kiem tra nhieu man hinh/thiet bi.
