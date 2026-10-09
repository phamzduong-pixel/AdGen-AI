# AdGen AI

AdGen AI là ứng dụng tạo, đánh giá và quản lý nội dung quảng cáo bằng Gemini.
Ứng dụng hỗ trợ hội thoại SSE, thư viện nội dung, thư viện mẫu quảng cáo,
phiên bản A/B, dashboard, chiến dịch, hồ sơ, cài đặt người dùng,
và module **AdGen Voice Studio** (Text-to-Speech / Voiceover Generator chuyên biệt cho kịch bản quảng cáo).

## Công nghệ

- Frontend: React 19, Vite, Axios
- Backend: FastAPI, SQLAlchemy, JWT
- AI: Gemini
- Streaming: Server-Sent Events qua Fetch API
- Database: SQLite khi phát triển, PostgreSQL khi triển khai
- Migration: Alembic
- Container: Docker, Docker Compose, Nginx

## Cấu trúc chính

```text
AdGenAI/
├── backend/
│   ├── alembic/              # Migration database
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── core/             # Cấu hình và bảo mật
│   │   ├── database/         # Engine và session
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Request/response schemas
│   │   └── services/         # Nghiệp vụ, AI và storage adapter
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── services/
│   └── Dockerfile
└── docker-compose.yml
```

## Chạy local không dùng Docker

Yêu cầu Python 3.12+, Node.js 20+ và Gemini API key.

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Thay các placeholder trong `backend/.env`, sau đó:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Backend chạy tại `http://localhost:8000`. SQLite cũ được nâng cấp bảo toàn dữ
liệu khi ứng dụng khởi động; không cần xóa `chatbot.db`.

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

`VITE_API_URL` là URL duy nhất dùng cho Axios, upload, download và SSE. Để bật
đăng nhập Google, đặt cùng một OAuth Web Client ID vào `GOOGLE_CLIENT_ID` của
backend và `VITE_GOOGLE_CLIENT_ID` của frontend.

## Database và migration

`DATABASE_URL` quyết định database:

```dotenv
# Local
DATABASE_URL=sqlite:///./chatbot.db

# Production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Chạy migration:

```powershell
cd backend
alembic upgrade head
alembic current
alembic check
```

Migration baseline dùng `checkfirst` và không xóa bảng/dữ liệu hiện hữu.
Hãy sao lưu database trước mọi migration production. Không chạy
`Base.metadata.drop_all()` hoặc xóa SQLite để cập nhật schema.

## Biến môi trường

Backend:

| Biến                                 |      Bắt buộc | Mô tả                                                |
| ------------------------------------ | ------------: | ---------------------------------------------------- |
| `SECRET_KEY`                         |            Có | Chuỗi ngẫu nhiên tối thiểu 32 ký tự                  |
| `ALGORITHM`                          |            Có | Thuật toán JWT, mặc định `HS256`                     |
| `ACCESS_TOKEN_EXPIRE_MINUTES`        |            Có | Thời hạn access token                                |
| `DATABASE_URL`                       |            Có | URL SQLite hoặc PostgreSQL                           |
| `GEMINI_API_KEY`                     |            Có | Chỉ lưu ở backend                                    |
| `GOOGLE_CLIENT_ID`                   |         Không | OAuth Web Client ID dùng để xác minh Google ID token |
| `SMTP_HOST`                          | Quên mật khẩu | SMTP server, mặc định `smtp.gmail.com`               |
| `SMTP_PORT`                          | Quên mật khẩu | SMTP port, mặc định `587`                            |
| `SMTP_USERNAME`                      | Quên mật khẩu | Địa chỉ Gmail/Workspace gửi OTP                      |
| `SMTP_PASSWORD`                      | Quên mật khẩu | Gmail App Password, không dùng mật khẩu thường       |
| `SMTP_FROM_EMAIL`                    | Quên mật khẩu | Địa chỉ người gửi hiển thị trong email               |
| `SMTP_FROM_NAME`                     |         Không | Tên người gửi, mặc định `AdGen AI`                   |
| `SMTP_USE_TLS`                       |         Không | Dùng STARTTLS, mặc định `true`                       |
| `PASSWORD_RESET_CODE_EXPIRE_MINUTES` |         Không | Thời hạn OTP/reset token, mặc định 10 phút           |
| `PASSWORD_RESET_RESEND_SECONDS`      |         Không | Thời gian chờ gửi lại, mặc định 60 giây              |
| `PASSWORD_RESET_MAX_ATTEMPTS`        |         Không | Số lần nhập OTP sai tối đa, mặc định 5               |
| `EMAIL_VERIFICATION_EXPIRE_MINUTES`  |         Không | Thời hạn mã xác minh email, mặc định 10 phút         |
| `EMAIL_VERIFICATION_RESEND_SECONDS`  |         Không | Thời gian chờ gửi lại mã, mặc định 60 giây           |
| `EMAIL_VERIFICATION_MAX_ATTEMPTS`    |         Không | Số lần nhập mã sai tối đa, mặc định 5                |
| `ALLOWED_ORIGINS`                    |            Có | Danh sách origin, phân tách bằng dấu phẩy            |
| `UPLOAD_DIR`                         |            Có | Thư mục lưu file có persistent storage               |
| `MAX_UPLOAD_SIZE`                    |            Có | Dung lượng tối đa theo byte                          |
| `ENVIRONMENT`                        |            Có | `development`, `test` hoặc `production`              |
| `PORT`                               |    Production | Port của Uvicorn/container                           |

Frontend:

| Biến                    | Bắt buộc | Mô tả                                                      |
| ----------------------- | -------: | ---------------------------------------------------------- |
| `VITE_API_URL`          |       Có | URL public của backend, không có dấu `/` cuối              |
| `VITE_GOOGLE_CLIENT_ID` |    Không | OAuth Web Client ID công khai của Google Identity Services |

Không commit `.env`, database, upload, JWT hoặc API key. Google Client Secret
không được dùng trong frontend và không cần thiết cho luồng GIS hiện tại.

## Cấu hình đăng nhập Google

1. Mở [Google Auth Platform](https://console.cloud.google.com/auth/overview),
   chọn hoặc tạo một Google Cloud project và hoàn tất **Branding/Audience**.
2. Trong **Clients**, tạo client loại **Web application**.
3. Thêm các origin frontend vào **Authorized JavaScript origins**, ví dụ
   `http://localhost:5173` và URL public của `adgen-ai-web`. Chỉ nhập origin,
   không thêm path hoặc dấu `/` cuối.
4. Sao chép Client ID có đuôi `.apps.googleusercontent.com` vào:

```dotenv
# backend/.env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# frontend/.env
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

5. Khởi động lại backend và frontend. Với Vite, biến `VITE_*` được đóng vào
   bundle lúc build nên phải build/deploy lại frontend sau khi đổi Client ID.

Nút Google do Google Identity Services render. Frontend chỉ chuyển credential
ngắn hạn đến `POST /auth/google`; backend xác minh chữ ký, audience, issuer,
thời hạn và email đã xác minh rồi mới cấp JWT AdGen AI. Credential Google không
được lưu vào local storage. Nếu chưa cấu hình Client ID, nút Google bị vô hiệu
hóa nhưng đăng nhập local vẫn hoạt động.

## Quên mật khẩu qua Gmail OTP

Luồng khôi phục gồm `/forgot-password` → `/verify-reset-code` →
`/reset-password`. Backend cung cấp:

- `POST /auth/forgot-password`
- `POST /auth/verify-reset-code`
- `POST /auth/reset-password`

OTP 6 số và reset token chỉ được lưu dạng HMAC hash, có thời hạn, dùng một lần.
Đổi mật khẩu thành công tăng `token_version`, vì vậy các access token cũ bị vô
hiệu hóa. Frontend chỉ giữ reset token tạm thời trong `sessionStorage` và xóa
sau khi hoàn tất.

Cấu hình `backend/.env`:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-account@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your-account@gmail.com
SMTP_FROM_NAME=AdGen AI
SMTP_USE_TLS=true
PASSWORD_RESET_CODE_EXPIRE_MINUTES=10
PASSWORD_RESET_RESEND_SECONDS=60
PASSWORD_RESET_MAX_ATTEMPTS=5
PASSWORD_RESET_EMAIL_HOURLY_LIMIT=5
PASSWORD_RESET_IP_HOURLY_LIMIT=20
EMAIL_VERIFICATION_EXPIRE_MINUTES=10
EMAIL_VERIFICATION_RESEND_SECONDS=60
EMAIL_VERIFICATION_MAX_ATTEMPTS=5
```

Để tạo Gmail App Password:

1. Bật **2-Step Verification** cho tài khoản Google gửi email.
2. Mở [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Tạo App Password riêng cho `AdGen AI`, sao chép mã 16 ký tự vào
   `SMTP_PASSWORD` và khởi động lại backend.

Không commit App Password. Nếu tùy chọn App Password không xuất hiện, tài khoản
có thể đang dùng Advanced Protection, chỉ dùng security key, hoặc bị chính sách
Google Workspace chặn.

Chống spam hiện tại dùng bộ nhớ của từng process: tối thiểu 60 giây giữa hai yêu
cầu cùng email, tối đa 5 yêu cầu/email/giờ và 20 yêu cầu/IP/giờ. Khi triển khai
nhiều worker/instance, cần chuyển rate-limit state sang Redis hoặc reverse proxy
để giới hạn có hiệu lực toàn cụm.

## Build và chạy production

### Backend

Đặt `ENVIRONMENT=production`, dùng PostgreSQL và persistent volume cho upload:

```powershell
cd backend
alembic upgrade head
$env:PORT = "8000"
uvicorn app.main:app --host 0.0.0.0 --port $env:PORT --workers 2
```

Không dùng `--reload`. Nếu nền tảng tự cung cấp biến `PORT`, truyền biến đó vào
lệnh Uvicorn. Chạy migration một lần trước khi chuyển traffic sang phiên bản mới.

### Frontend

Đặt `VITE_API_URL=https://api.example.com` và, nếu dùng Google,
`VITE_GOOGLE_CLIENT_ID` trong build environment:

```powershell
cd frontend
npm ci
npm run build
```

Triển khai nội dung `frontend/dist` lên static hosting. Hosting phải fallback các
route `/chat`, `/dashboard`, `/library`, `/templates`, `/campaigns`,
`/settings`, `/profile`, `/forgot-password`, `/verify-reset-code` và
`/reset-password` về `index.html`. `public/_redirects` và `nginx.conf`
đã có cấu hình SPA tương ứng.

## Docker Compose

Tạo cấu hình:

```powershell
Copy-Item .env.example .env
```

Thay `POSTGRES_PASSWORD`, `SECRET_KEY`, `GEMINI_API_KEY`. Để bật Google Login,
đặt `GOOGLE_CLIENT_ID` và `VITE_GOOGLE_CLIENT_ID` bằng cùng một Web Client ID.
Nếu password database
có ký tự đặc biệt, URL-encode khi dùng trực tiếp trong `DATABASE_URL`.
Để bật quên mật khẩu, nhập thêm các biến `SMTP_*`; không dùng mật khẩu Gmail
thông thường.

Chạy toàn hệ thống:

```powershell
docker compose up --build
docker compose ps
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- PostgreSQL và upload dùng named volume, không mất khi container được tạo lại.

Dừng container nhưng giữ dữ liệu:

```powershell
docker compose down
```

Không dùng `docker compose down -v` nếu muốn giữ database và file upload.

## Chia sẻ public bằng Render Blueprint

File `render.yaml` ở thư mục gốc tự tạo:

- `adgen-ai-web`: React/Vite Static Site
- `adgen-ai-api`: FastAPI Docker Web Service
- `adgen-ai-db`: PostgreSQL

Sau khi push repository lên GitHub:

1. Trong Render chọn **New → Blueprint**.
2. Kết nối repository và chọn `render.yaml`.
3. Nhập `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`,
   `VITE_GOOGLE_CLIENT_ID` khi Render yêu cầu. Hai biến Google dùng cùng Client ID.
   Nhập thêm `SMTP_USERNAME`, `SMTP_PASSWORD` và `SMTP_FROM_EMAIL` để gửi OTP.
4. Kiểm tra kế hoạch tài nguyên rồi chọn **Apply**.
5. Khi deploy xong, mở URL của `adgen-ai-web`.

Render tự sinh `SECRET_KEY`, nối `DATABASE_URL`, đưa URL backend vào
`VITE_API_URL` và đưa URL frontend vào `ALLOWED_ORIGINS`. Không nhập secret vào
Git hoặc sửa chúng thành giá trị cố định trong Blueprint.

Sau khi có URL frontend thật, thêm chính origin đó vào **Authorized JavaScript
origins** trong Google Cloud rồi redeploy static site. Kiểm tra bằng cửa sổ ẩn
danh: đăng nhập một Google user mới, đăng xuất, sau đó đăng nhập lại cùng email
và xác nhận hệ thống không tạo user trùng.

Blueprint dùng gói free cho bản demo. Backend có thể sleep khi không hoạt động,
PostgreSQL free có giới hạn vòng đời theo chính sách hiện hành, và file upload
trên filesystem sẽ không bền qua redeploy. Chuyển backend/database sang gói trả
phí và gắn persistent disk tại `/app/uploads` trước khi dùng lâu dài.

## Health check

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Kết quả:

```json
{ "status": "ok", "service": "adgen-ai-api" }
```

Health check không trả secret, database URL hoặc cấu hình nội bộ.

## Kiểm tra trước khi deploy

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m compileall -q app alembic
alembic upgrade head
alembic check

cd ..\frontend
npm test
npm run lint
npm run build
```

Các test AI dùng mock và không tiêu thụ Gemini quota.

## CORS, SSE và upload

- `ALLOWED_ORIGINS` phải chứa chính xác origin frontend public và các origin local
  cần dùng; không dùng wildcard khi gửi JWT.
- SSE dùng Fetch API, `Authorization` header và `AbortController`, phù hợp HTTPS.
- Reverse proxy cần tắt response buffering cho endpoint streaming và cho phép
  request tồn tại đủ lâu.
- Upload được kiểm tra extension, MIME, dung lượng, UUID và quyền sở hữu.
- File chỉ được tải qua endpoint có JWT; thư mục upload không được public trực tiếp.

## Giới hạn bản demo

- Access token chưa có refresh token; khi hết hạn người dùng phải đăng nhập lại.
- Khôi phục qua số điện thoại/SMS chưa triển khai vì cần nhà cung cấp có chi phí;
  phiên bản hiện tại chỉ kích hoạt `EmailOTPProvider`.
- Local storage adapter yêu cầu persistent disk. Filesystem tạm thời của một số
  nền tảng sẽ làm mất file sau restart/deploy; khi mở rộng nên thay adapter bằng
  S3 hoặc dịch vụ object storage tương đương.
- SQLite chỉ phù hợp local hoặc demo một instance. Public deployment nên dùng
  PostgreSQL.
- Frontend bundle hiện còn tương đối lớn; có thể bổ sung route-level code splitting.
- Cần giới hạn quota/rate limit ở reverse proxy hoặc nền tảng hosting trước khi
  mở demo rộng rãi để bảo vệ Gemini quota.

## Trạng thái bàn giao: Cài đặt

Cập nhật lần cuối: **08/09/2026**.

| Phần | Trạng thái | Nội dung hiện tại |
| --- | --- | --- |
| Bố cục và cuộn trang | Hoàn thành | Khung gốc tự giãn theo nội dung; workspace không còn bị cắt nền/viền khi cuộn; có khoảng an toàn cuối trang trên desktop và mobile. |
| Giao diện sáng/tối/hệ thống | Hoàn thành | Áp dụng ngay qua `ThemeContext` và lưu lựa chọn an toàn ở local storage. |
| Tùy chọn Chat | Hoàn thành | Tự động cuộn, hiển thị thời gian, xác nhận trước khi xóa và mở hội thoại gần nhất đã được sử dụng trong luồng Chat. |
| Tùy chọn AI | Hoàn thành | Nền tảng, giọng văn, ngôn ngữ và độ dài đã lưu local, đồng bộ backend và tự động điền vào biểu mẫu thông tin quảng cáo. |
| Xuất dữ liệu | Hoàn thành | Markdown, TXT, PDF và tùy chọn kèm thời gian đã có. Tự động áp dụng định dạng xuất mặc định tại các điểm xuất dữ liệu. |
| Đổi mật khẩu | Hoàn thành | Kiểm tra xác nhận mật khẩu, gọi backend và kết thúc phiên hiện tại sau khi đổi thành công. |
| Quản lý thiết bị đăng nhập | Hoàn thành | Tải lại danh sách, thu hồi từng phiên và đăng xuất khỏi tất cả thiết bị. |
| Đồng bộ và xử lý lỗi | Hoàn thành | Cài đặt tài khoản được đọc/ghi qua API; tùy chọn giao diện/Chat có giá trị mặc định an toàn khi local storage thiếu hoặc hỏng. |
| Responsive và dark mode | Hoàn thành | Các thẻ co giãn đúng chiều rộng, form đổi mật khẩu chuyển một cột và nội dung cuối trang không bị thanh điều hướng mobile che. |
| Kiểm tra tự động | Đạt | ESLint đạt 100%, 97/97 backend tests đạt, 23/23 frontend tests đạt, alembic check đạt chuẩn và production build thành công. |

## Trạng thái chuẩn hóa hệ thống & Nghiệp vụ Gen AI (08/09/2026)

Section này đã hoàn thành toàn diện việc rà soát kỹ thuật, dọn dẹp mã nguồn thừa và tinh chỉnh nghiệp vụ để phục vụ báo cáo:

1. **Database Schema & Migration**:
   - Khắc phục triệt để lỗi lệch schema khi chạy `alembic check`.
   - Bổ sung migration chuẩn `20260727_0008_campaign_primary_index.py` tạo partial unique index `uq_content_documents_campaign_primary` trên bảng `content_documents`.
   - Kết quả: `alembic check` báo `No new upgrade operations detected`, mã thoát `0`.

2. **Dọn dẹp mã rác & Cấu trúc thư mục (Dead Code Elimination)**:
   - Xóa bỏ toàn bộ thư mục skeleton `backend/app/ai/` (`gemini.py`, `prompt_engine.py`, `templates.py`) không sử dụng.
   - Xóa bỏ thư mục rỗng `backend/app/utils/`.
   - Cấu trúc `backend/app/` được tinh gọn thành 10 module chức năng rõ ràng, chuẩn phong cách FastAPI.

3. **Khắc phục cảnh báo Deprecation (`datetime.utcnow()`)**:
   - Xây dựng module tập trung `app.core.datetime_utils.utc_now` tương thích chuẩn Python 3.12+.
   - Cập nhật đồng bộ trên 12 Models và 6 Services (`security`, `session_service`, `password_reset_service`, `email_verification_service`, `dashboard_service`, `user_service`).
   - Triệt tiêu 100% cảnh báo `DeprecationWarning` khi chạy test và server.

4. **Nâng cấp chất lượng nghiệp vụ Prompt & AI Learning Dataset**:
   - Nâng cấp `backend/app/prompts/instagram.py` đạt chuẩn quảng cáo chuyên nghiệp (Visual Concept, Hook mở đầu, cấu trúc Caption, CTA chuyển đổi và chiến lược Hashtag 3 tầng).
   - Bổ sung cơ chế lưu trữ bền vững JSON Lines cho `LearningDatasetService` tại `backend/data/learning_dataset.jsonl`, bảo toàn dữ liệu đánh giá và tinh chỉnh AI (Evaluation, Fine-tuning).

5. **Hoàn thiện giao diện người dùng Frontend**:
   - `AdBriefForm`: Tự động áp dụng các cài đặt mặc định (`defaultTone`, `defaultLanguage`, `defaultLength`) vào form khi tạo yêu cầu quảng cáo mới.
   - `exportConversation.js` & `Chat.jsx`: Chuẩn hóa cú pháp import và tự động áp dụng định dạng xuất mặc định đã lưu khi xuất nhanh lịch sử hội thoại.
   - Sửa lỗi lint `react-hooks/set-state-in-effect` theo chuẩn React.

6. **Kết quả kiểm thử toàn diện**:
   - Backend Tests: **97/97 tests pass** trong 54.5s (0 lỗi, 0 cảnh báo).
   - Frontend Tests: **23/23 tests pass**.
   - ESLint: **0 lỗi, 0 cảnh báo**.
   - Production Build: **573 modules build thành công** trong 2.4s.



## Runtime hardening và quy trình database hiện hành

Database rỗng và database đã có dữ liệu dùng hai quy trình khác nhau. Với database hoàn toàn rỗng và disposable, chạy `python -m app.database.bootstrap --confirm-empty` (hoặc `python -m app.database.prepare_database`) trong `backend`; lệnh chỉ tạo schema sau khi validate manifest/model và không sửa database đã tồn tại. Với database đã có dữ liệu ở revision hợp lệ, backup trước rồi chạy `alembic upgrade head` để áp dụng migration mới. Schema legacy/lệch/không rõ lịch sử sẽ bị fail-closed và cần báo cáo chỉ đọc bằng `python -m app.database.legacy_reconciliation`.

Không sửa migration đã phát hành, không stamp để che mismatch, không drop bảng và không xóa database. Backend Docker chạy bước chuẩn bị database trước Uvicorn; Docker Compose dùng PostgreSQL volume, còn Render dùng PostgreSQL managed và frontend build bằng `npm ci` từ lockfile. Frontend đã đồng bộ lockfile với Node 22/npm 10.9.2; kiểm tra sạch bằng `npx --yes npm@10.9.2 ci`, `npm test`, `npm run lint`, `npm run build`.

Voice Studio yêu cầu JWT cho generate và stream/download audio. Audio legacy không có owner bị từ chối; frontend dùng Axios Blob với header xác thực, không đưa JWT vào URL. Gemini được dùng qua API; learning dataset chỉ là dữ liệu ghi nhận cho đánh giá/quy trình huấn luyện riêng, không đồng nghĩa tự training/fine-tuning. Trend registry không tự thu thập trend trực tuyến. Regex validator chỉ là heuristic, không bảo đảm claim đúng sự thật.

Xem quy trình đầy đủ tại [docs/01-chuc-nang-he-thong.md](docs/01-chuc-nang-he-thong.md).
## Cập nhật giao diện và nhận diện thương hiệu — 04/10/2026

Đã đồng bộ màu logo thương hiệu và giao diện Chat với Login/Register cho cả light, dark và system dark. Logo DG tại Sidebar, Login/Register, Recovery và Workspace dùng nền lavender/indigo thống nhất; biểu tượng thương hiệu ở Chat dùng cùng token. Logo tia sét trong tiêu đề Chat đã được bỏ; avatar người dùng vẫn độc lập. Kiểm tra sau cập nhật: `npm run lint` PASS, `npm test` PASS (38/38), `npm run build` PASS.