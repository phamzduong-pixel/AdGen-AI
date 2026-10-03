# 6. Triển khai và vận hành

## 6.1. Biến môi trường

### Backend bắt buộc

| Biến | Ý nghĩa |
| --- | --- |
| `SECRET_KEY` | JWT secret, tối thiểu 32 ký tự ngẫu nhiên |
| `DATABASE_URL` | SQLite hoặc PostgreSQL URL |
| `GEMINI_API_KEY` | API key, chỉ giữ ở backend |
| `ALLOWED_ORIGINS` | danh sách origin frontend, phân cách bằng dấu phẩy |
| `UPLOAD_DIR` | thư mục lưu file persistent |
| `MAX_UPLOAD_SIZE` | kích thước upload tối đa theo byte |
| `ENVIRONMENT` | `development`, `test` hoặc `production` |

### Backend tùy chọn

`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GOOGLE_CLIENT_ID`, các biến `SMTP_*`, nhóm `PASSWORD_RESET_*`, nhóm `EMAIL_VERIFICATION_*` và `PORT`.

### Frontend

- `VITE_API_URL`: URL public của backend.
- `VITE_GOOGLE_CLIENT_ID`: Google Web Client ID công khai, tùy chọn.

Không commit `.env`, database, upload, JWT, Gemini API key, SMTP password hoặc Google secret.

## 6.2. Local không Docker

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.database.bootstrap --confirm-empty
uvicorn app.main:app --reload
```

Terminal khác:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

## 6.3. Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
docker compose ps
```

Services:

- `db`: PostgreSQL 17 Alpine.
- `backend`: FastAPI port `8000`, volume `/app/uploads`.
- `frontend`: Vite build và Nginx port `5173`.

`docker compose down` giữ named volumes. Chỉ dùng `down -v` khi thực sự muốn xóa database và upload.

## 6.4. Render Blueprint

`render.yaml` tạo `adgen-ai-api` (Docker web service), `adgen-ai-web` (static site rewrite về `index.html`) và `adgen-ai-db` (PostgreSQL). Render tự nối `DATABASE_URL`, `VITE_API_URL`, `ALLOWED_ORIGINS` và sinh `SECRET_KEY`. Cần nhập `GEMINI_API_KEY`; Google/SMTP nhập nếu dùng.

Upload trên filesystem free plan không bền qua redeploy nếu không có persistent disk.

## 6.5. Migration và kiểm tra trước deploy

```powershell
cd backend
alembic upgrade head
alembic current
alembic check
python -m unittest discover -s tests -v
python -m compileall -q app alembic

cd ..\frontend
npm test
npm run lint
npm run build
```

AI tests dùng mock, không nên tiêu thụ Gemini quota. Migration production cần backup trước và chạy một lần trước khi chuyển traffic.

## 6.6. Vận hành an toàn

- Cấu hình HTTPS cho frontend/backend public.
- CORS chỉ cho phép origin hợp lệ.
- Reverse proxy tắt buffering cho stream.
- Theo dõi quota/429 và thời gian phản hồi Gemini.
- Backup cả PostgreSQL và volume upload.
- Khi chạy nhiều worker, chuyển OTP rate-limit state khỏi memory process.
- Không expose thư mục upload trực tiếp qua static server.

## 6.7. Quy trình local hiện tại sau Plan 09

Runtime backend không còn tự động tạo hoặc sửa schema khi khởi động. Với một
database local hoàn toàn mới, dùng quy trình explicit sau:

```powershell
cd backend
python -m app.database.bootstrap --confirm-empty
uvicorn app.main:app --reload
```

Lệnh bootstrap chỉ được chạy trên database đã xác nhận là rỗng và disposable.
Không dùng lệnh này cho `chatbot.db`, database production hoặc database có dữ
liệu cần bảo toàn. Với database cũ hoặc không rõ lịch sử, chạy báo cáo chỉ đọc:

```powershell
python -m app.database.legacy_reconciliation
```

Không dùng `alembic upgrade head` trực tiếp để thay thế bootstrap trên SQLite
local mới trong trạng thái hiện tại. Chuỗi migration lịch sử `0001–0016` còn
xung đột: revision `0001` tạo trước các object của revision sau và `0008` có
thể tạo trùng index. Lịch sử này chưa được viết lại vì chưa có bằng chứng an
toàn cho mọi database đã phát hành.

## 6.8. Quy trình runtime đã đồng bộ

`backend/Dockerfile` chạy `python -m app.database.prepare_database` trước Uvicorn. Database rỗng được bootstrap từ schema đã validate; database canonical hiện hữu chỉ được kiểm tra; mọi schema legacy/lệch đều làm container dừng để tránh tự sửa dữ liệu. Database đã có dữ liệu cần nâng cấp phải chạy `alembic upgrade head` sau backup trước khi deploy. Không dùng `stamp`, `drop_all()` hoặc xóa database để vượt qua lỗi schema.

Frontend dùng Node 22 và npm 10.9.2 để tạo lockfile ổn định. Render giữ `npm ci && npm run build`; chạy clean install/test/lint/build như hướng dẫn ở `docs/15-runtime-hardening-and-handoff.md`.