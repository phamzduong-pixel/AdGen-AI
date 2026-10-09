# Tài liệu hệ thống AdGen AI

> Phiên bản tài liệu: 10/10/2026
> Phạm vi: mã nguồn hiện tại trong repository `AdGenAI`

Thư mục này là bộ tài liệu kỹ thuật đồng bộ với hệ thống đang có. Mỗi tài liệu trỏ về module hoặc file nguồn liên quan để dễ kiểm tra khi mã nguồn thay đổi.

## Mục lục

| Tài liệu | Nội dung |
| --- | --- |
| [00-tong-quan-he-thong.md](./00-tong-quan-he-thong.md) | Báo cáo tổng hợp hệ thống, kiến trúc, Gen AI, dữ liệu, vận hành, kiểm thử và giới hạn hiện tại |
| [01-chuc-nang-he-thong.md](./01-chuc-nang-he-thong.md) | Các chức năng người dùng, frontend và backend |
| [02-luong-xu-ly-ai.md](./02-luong-xu-ly-ai.md) | Luồng AI từ brief/tin nhắn đến kết quả |
| [03-co-so-du-lieu.md](./03-co-so-du-lieu.md) | Mô hình dữ liệu, quan hệ, ràng buộc và migration |
| [04-api-va-frontend.md](./04-api-va-frontend.md) | Các nhóm API, route giao diện và quy ước tích hợp |
| [05-trien-khai-va-van-hanh.md](./05-trien-khai-va-van-hanh.md) | Chạy local, Docker, Render, biến môi trường và kiểm tra |
| [06-quy-uoc-dong-bo-tai-lieu.md](./06-quy-uoc-dong-bo-tai-lieu.md) | Cách cập nhật tài liệu khi hệ thống thay đổi |
| [07-huong-dan-su-dung-he-thong.md](./07-huong-dan-su-dung-he-thong.md) | Hướng dẫn sử dụng toàn bộ chức năng hệ thống |
| [08-vai-tro-cac-chuc-nang.md](./08-vai-tro-cac-chuc-nang.md) | Vai trò và giá trị của các chức năng chính |
| [09-voice-studio-audio-transform-plan.md](./09-voice-studio-audio-transform-plan.md) | Kế hoạch và trạng thái triển khai Voice Studio/Seed-VC |
| [10-adgen-ai-capstone-final-report.md](./10-adgen-ai-capstone-final-report.md) | Báo cáo Capstone và bằng chứng source/test hiện có |
| [PROJECT_TREE.md](./PROJECT_TREE.md) | Cây thư mục hệ thống và các vị trí chính của hệ thống |

## Nguồn sự thật

- Backend entrypoint/router: `backend/app/main.py`, `backend/app/api/`.
- Nghiệp vụ: `backend/app/services/`.
- Mô hình dữ liệu: `backend/app/models/`.
- Request/response: `backend/app/schemas/`.
- Database schema theo phiên bản: `backend/alembic/versions/`.
- Giao diện: `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/services/api/`.
- Cấu hình chạy: `docker-compose.yml`, `render.yaml`, các file `.env.example`.

README ở thư mục gốc là hướng dẫn chạy nhanh; bộ `docs/` tập trung vào cấu tạo và nghiệp vụ.


## Trạng thái cần biết

- Backend dùng FastAPI, SQLAlchemy, Alembic, JWT và Gemini `gemini-2.5-flash`.
- Frontend dùng React/Vite, Axios; realtime dùng Fetch API stream.
- SQLite hỗ trợ local/test; PostgreSQL là lựa chọn production.
- Upload hiện lưu filesystem và cần persistent disk hoặc object storage khi triển khai lâu dài.
- Access token hiện chưa có refresh token; khi hết hạn người dùng đăng nhập lại.
- Voice Studio hỗ trợ Text → Edge TTS, File audio/video → STT → TTS, reference-voice TTS và nhánh Direct Voice Conversion qua Seed-VC khi file source không có transcript. Xem `01-chuc-nang-he-thong.md` và `09-voice-studio-audio-transform-plan.md`.
- Seed-VC đã có API/service/UI integration chạy CPU và fail-closed. Runtime local hiện chưa được xác nhận vì còn thiếu `SEED_VC_PYTHON`, `SEED_VC_DIR` và đầy đủ reference WAV.
- Các nhãn hiển thị cho người dùng dùng thương hiệu AdGen AI; tên provider/model kỹ thuật chỉ được giữ trong cấu hình hoặc thông báo kỹ thuật khi cần chẩn đoán.
- Canonical schema hiện có 34 bảng ứng dụng; migration head `20261006_0025_trend_report_history_soft_delete`.
- Trend Radar hiện bao gồm Trend Report, Product Trust, Monitor/Snapshot, Alert, Advertising Angle, Brief, Campaign Metric Snapshot và xóa lịch sử bằng soft-delete.

## Cập nhật vận hành gần nhất

- Local development hiện dùng database mới `backend/adgen_dev.db`; database cũ `chatbot.db` được giữ nguyên vì schema của nó lệch migration và chưa được repair tự động.
- Database mới được tạo bằng bootstrap explicit, đạt schema `PASS` và revision hiện tại `20261006_0025`.
- Runtime guard fail-closed: backend không tự tạo bảng, tự repair schema hoặc tự stamp database legacy.
- `python -m app.database.bootstrap --confirm-empty` chỉ dành cho database được xác nhận rỗng; `python -m app.database.legacy_reconciliation` chỉ đọc và báo cáo.
- Tài khoản demo local có username `AdGenAI`, email `adgenai@example.com`; không ghi mật khẩu vào tài liệu hoặc repository.
- Bubble tin nhắn người dùng đã được chỉnh về căn trái để nội dung dài xuống dòng đúng.


## Cập nhật kiểm tra hệ thống gần nhất

Ngày 10/10/2026, vòng audit toàn hệ thống đã sửa lỗi cú pháp cuối file Voice Studio, loại bỏ operation ID OpenAPI trùng, làm rõ import `ConversationItem` và chuẩn hóa whitespace/UTF-8 ở các file bị ảnh hưởng. Không xóa dữ liệu hay source nghiệp vụ.

Kết quả: frontend **68/68 tests PASS**, lint/build PASS; backend **495 tests PASS** và 74 subtests PASS; OpenAPI 97 paths, health check, CORS local, migration head, compile và dependency integrity đều PASS. Các cảnh báo deprecation không chặn runtime.
