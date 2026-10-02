# 7. Quy ước đồng bộ tài liệu

## 7.1. Nguyên tắc

Tài liệu phải mô tả hành vi đã có trong mã nguồn, không mô tả roadmap như tính năng đã hoàn thành. Khi có khác biệt, ưu tiên:

1. Code và schema/migration đang được chạy.
2. Test đang pass.
3. Cấu hình deploy (`docker-compose.yml`, `render.yaml`, `.env.example`).
4. README và tài liệu trong `docs/`.

## 7.2. Khi thay đổi code

| Thay đổi | Tài liệu cần xem lại |
| --- | --- |
| Thêm/sửa endpoint | `05-api-va-frontend.md`, `02-chuc-nang-he-thong.md` |
| Thêm/sửa AI/prompt | `03-luong-xu-ly-ai.md`, `02-chuc-nang-he-thong.md` |
| Thêm model/migration | `04-co-so-du-lieu.md` |
| Thêm page/hook/API client | `05-api-va-frontend.md`, `02-chuc-nang-he-thong.md` |
| Đổi env/deploy/runtime | `01-tong-quan-he-thong.md`, `06-trien-khai-va-van-hanh.md` |
| Đổi security/giới hạn | tài liệu liên quan và mục giới hạn |

## 7.3. Checklist cập nhật

- [ ] Đã kiểm tra file code nguồn tương ứng.
- [ ] Đã cập nhật đường dẫn module.
- [ ] Đã cập nhật endpoint/table/biến môi trường nếu có.
- [ ] Đã ghi rõ trạng thái đang có hay giới hạn/roadmap.
- [ ] Đã chạy test hoặc kiểm tra phù hợp.
- [ ] Đã cập nhật ngày phiên bản ở `docs/README.md`.
- [ ] Đã kiểm tra link Markdown nội bộ.

## 7.4. Quy ước viết

- Dùng tiếng Việt cho diễn giải; giữ nguyên tên class, service, endpoint, table và biến môi trường.
- Dùng path tương đối từ root repository để dev tìm nhanh.
- Không ghi secret, token, API key, SMTP password hoặc dữ liệu người dùng thật.
- Với provider bên ngoài, ghi provider hiện tại và fallback/mock nếu có.
- Với schema, mô tả ràng buộc và migration thay vì chỉ liệt kê tên bảng.

## 7.5. Kiểm tra nhanh

```powershell
rg --files docs
rg -n "@router|__tablename__|revision:|VITE_|GEMINI_|DATABASE_URL" backend frontend docker-compose.yml render.yaml
```

Sau đó chạy các lệnh trong [06-trien-khai-va-van-hanh.md](./06-trien-khai-va-van-hanh.md). Nếu endpoint hoặc table mới chưa được phản ánh, cập nhật tài liệu cùng commit với thay đổi code.
## 7.6. Cleanup filesystem — 30/09/2026

Đã rà soát reference trong toàn workspace và thực hiện cleanup an toàn, không refactor code, không thay đổi API, AI pipeline, migration hoặc dữ liệu người dùng.

Đã xóa hoàn toàn:

- `frontend/dist/`;
- `.pytest_cache/` và `backend/.pytest_cache/`;
- `frontendsrcpagesLoginLogin.css` và `frontendsrcpagesRegisterRegister.css` ở root;
- `backend/app/services/chat_service.py` — service legacy không được router/service nào tham chiếu.

Đã xóa phần lớn `frontend/node_modules/` và `backend/venv/`. Một số binary còn lại do Windows đang khóa bởi process `node`, `python` và `uvicorn`; không tự dừng process trong cleanup này. Có thể hoàn tất sau khi dừng các process đó, sau đó cài lại dependency khi cần.

Giữ nguyên:

- `backend/chatbot.db`, `backend/adgen.db`, `backend/uploads/`, `backend/.env`, `frontend/.env`;
- toàn bộ scaffold/utility frontend đã được đánh dấu giữ lại;
- prompts, context engine, knowledge base, learning dataset, output validator, platform intelligence, product aware, trend intelligence, voiceover, Alembic và tests.

Build/test không chạy lại sau cleanup vì dependency local đã bị xóa theo yêu cầu; không tự cài lại dependency. Không commit và không push.
