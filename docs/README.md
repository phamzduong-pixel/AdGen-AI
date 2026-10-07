# Tài liệu hệ thống AdGen AI

> Phiên bản tài liệu: 06/10/2026
> Phạm vi: mã nguồn hiện tại trong repository `AdGenAI`

Thư mục này là bộ tài liệu kỹ thuật đồng bộ với hệ thống đang có. Mỗi tài liệu trỏ về module hoặc file nguồn liên quan để dễ kiểm tra khi mã nguồn thay đổi.

## Mục lục

| Tài liệu | Nội dung |
| --- | --- |
| [00-tong-quan-he-thong.md](./00-tong-quan-he-thong.md) | Báo cáo tổng hợp hệ thống, kiến trúc, Gen AI, dữ liệu, vận hành, kiểm thử và giới hạn hiện tại |
| [02-chuc-nang-he-thong.md](./02-chuc-nang-he-thong.md) | Các chức năng người dùng, frontend và backend |
| [03-luong-xu-ly-ai.md](./03-luong-xu-ly-ai.md) | Luồng AI từ brief/tin nhắn đến kết quả |
| [04-co-so-du-lieu.md](./04-co-so-du-lieu.md) | Mô hình dữ liệu, quan hệ, ràng buộc và migration |
| [05-api-va-frontend.md](./05-api-va-frontend.md) | Các nhóm API, route giao diện và quy ước tích hợp |
| [06-trien-khai-va-van-hanh.md](./06-trien-khai-va-van-hanh.md) | Chạy local, Docker, Render, biến môi trường và kiểm tra |
| [07-quy-uoc-dong-bo-tai-lieu.md](./07-quy-uoc-dong-bo-tai-lieu.md) | Cách cập nhật tài liệu khi hệ thống thay đổi |
| [15-runtime-hardening-and-handoff.md](./15-runtime-hardening-and-handoff.md) | Báo cáo bàn giao runtime, bảo mật endpoint, database bootstrap, kiểm thử và nhận diện giao diện |
| [PROJECT_TREE.md](./PROJECT_TREE.md) | Cây thư mục hệ thống và các vị trí chính của Plan 17 |

| [09-ke-hoach-tao-anh-video.md](./09-ke-hoach-tao-anh-video.md) | Kế hoạch tạo ảnh, tạo video và chỉnh sửa video |
| [16-huong-dan-su-dung-he-thong.md](./16-huong-dan-su-dung-he-thong.md) | Hướng dẫn sử dụng toàn bộ chức năng từ tài khoản, Chat, media, editor, thương hiệu, chiến dịch đến cài đặt |
| [18-vai-tro-cac-chuc-nang.md](./18-vai-tro-cac-chuc-nang.md) | Vai trò, giá trị và thời điểm sử dụng các chức năng chính dành cho người dùng |
| [17-plan-adgen-trend-radar.md](./17-plan-adgen-trend-radar.md) | Plan 17 Trend Radar: Stage 1–4 đã hoàn thành; Alembic head `20261006_0024` |
| [19-voice-studio-audio-transform-plan.md](./19-voice-studio-audio-transform-plan.md) | Kế hoạch mở rộng Voice Studio: Content Source, Voice Source và Audio Transform; hiện ở trạng thái thiết kế |

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
- Voice Studio hiện hỗ trợ làm sạch/trích xuất lời thoại deterministic, fallback có kiểm soát, chỉnh sửa và tạo voiceover từ Text → TTS; xem chi tiết trong `00-tong-quan-he-thong.md` và `16-huong-dan-su-dung-he-thong.md`.
- Kế hoạch Audio → Target Voice và Filtered Text → User Voice trong `19-voice-studio-audio-transform-plan.md` chưa triển khai.

## Cập nhật vận hành gần nhất

- Local development hiện dùng database mới `backend/adgen_dev.db`; database cũ `chatbot.db` được giữ nguyên vì schema của nó lệch migration và chưa được repair tự động.
- Database mới được tạo bằng bootstrap explicit, đạt schema `PASS` và revision `20261001_0016`.
- Runtime guard fail-closed: backend không tự tạo bảng, tự repair schema hoặc tự stamp database legacy.
- `python -m app.database.bootstrap --confirm-empty` chỉ dành cho database được xác nhận rỗng; `python -m app.database.legacy_reconciliation` chỉ đọc và báo cáo.
- Tài khoản demo local có username `AdGenAI`, email `adgenai@example.com`; không ghi mật khẩu vào tài liệu hoặc repository.
- Bubble tin nhắn người dùng đã được chỉnh về căn trái để nội dung dài xuống dòng đúng.


## Cap nhat giao dien gan nhat

Ngay 05/10/2026, frontend da hoan tat tinh chinh mau nut tao hoi thoai, bo duong ke header Chat va dong bo bang mau dark mode cho cac surface chinh. Kiem tra frontend: lint PASS, 38 test PASS, build PASS.

Chi tiet implementation duoc ghi trong `15-runtime-hardening-and-handoff.md` va `16-huong-dan-su-dung-he-thong.md`.
