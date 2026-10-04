# Hướng dẫn sử dụng hệ thống AdGen AI

> Phiên bản tài liệu: 04/10/2026  
> Phạm vi: các chức năng đang có trong frontend/backend của repository hiện tại.

AdGen AI là trợ lý tạo và quản lý nội dung quảng cáo bằng AI. Người dùng có thể tạo nội dung theo hội thoại hoặc brief có cấu trúc, áp dụng quy chuẩn thương hiệu, đánh giá chất lượng, tạo biến thể, lưu thành thư viện, gom vào chiến dịch và tạo các tài sản media như ảnh, video hoặc voiceover.

## 1. Bắt đầu nhanh

Quy trình khuyến nghị:

1. Tạo tài khoản hoặc đăng nhập.
2. Vào **Hồ sơ thương hiệu** để khai báo giọng điệu, từ khóa, CTA và các từ không được dùng.
3. Vào **Cài đặt** để chọn mặc định về nền tảng, ngôn ngữ, giọng văn, độ dài và định dạng xuất.
4. Mở **Chat**, tạo cuộc hội thoại mới và nhập brief hoặc yêu cầu tự nhiên.
5. Kiểm tra phản hồi bằng **Đánh giá**, **Kiểm tra thương hiệu** hoặc tạo **A/B**.
6. Lưu nội dung cần dùng vào **Thư viện**, sau đó đưa vào **Chiến dịch** nếu cần quản lý theo nhóm.
7. Mở trình soạn thảo để chỉnh sửa, lưu phiên bản và xuất file.

Ứng dụng mặc định mở tại `/login`. Các khu vực làm việc yêu cầu người dùng đã đăng nhập.

## 2. Tài khoản và truy cập

### 2.1. Đăng ký

1. Chọn **Đăng ký** trên màn hình đăng nhập.
2. Nhập tên đăng nhập, email, mật khẩu và xác nhận mật khẩu.
3. Mật khẩu cần có tối thiểu 8 ký tự; tên đăng nhập phải là duy nhất.
4. Gửi biểu mẫu. Nếu hệ thống yêu cầu xác minh email, mở email xác minh hoặc vào `/verify-email` để hoàn tất.

Người dùng cũng có thể chọn **Tiếp tục bằng Google** nếu hệ thống đã được cấu hình Google OAuth.

### 2.2. Đăng nhập và đăng xuất

- Đăng nhập bằng email hoặc tên đăng nhập cùng mật khẩu.
- Chọn Google Login để xác thực bằng tài khoản Google đã cấu hình.
- Trong menu tài khoản ở cuối thanh bên, chọn **Đăng xuất**.
- Nếu access token hết hạn, đăng nhập lại để tiếp tục. Phiên bản hiện tại chưa có refresh token tự động.

### 2.3. Quên và đổi mật khẩu

1. Ở màn hình đăng nhập chọn **Quên mật khẩu?**.
2. Nhập email và yêu cầu mã OTP.
3. Nhập OTP 6 số tại màn hình xác minh mã.
4. Đặt mật khẩu mới tại màn hình reset password.

Mã OTP có thời hạn và giới hạn số lần nhập/số lần gửi lại. Nếu không nhận được email, kiểm tra Spam hoặc liên hệ người vận hành để kiểm tra SMTP.

Mật khẩu đang đăng nhập có thể đổi trong **Cài đặt → Bảo mật → Đổi mật khẩu**. Sau khi đổi, các phiên cũ có thể bị vô hiệu hóa và cần đăng nhập lại.

## 3. Bố cục và điều hướng

Sau khi đăng nhập, thanh điều hướng chính gồm:

| Khu vực | Mục đích |
| --- | --- |
| **Chat** | Tạo nội dung, chỉnh sửa phản hồi, đánh giá, A/B, voiceover và media |
| **Dashboard** | Xem tổng quan hoạt động, số lượng nội dung và nền tảng sử dụng |
| **Thư viện** | Tìm, xem, sao chép, sửa, xuất hoặc xóa nội dung đã lưu |
| **Mẫu quảng cáo** | Dùng mẫu có sẵn hoặc tạo mẫu cá nhân |
| **Hồ sơ thương hiệu** | Quản lý voice, guideline, tài sản và kiểm tra nhất quán thương hiệu |
| **Chiến dịch** | Gom nội dung đã lưu theo sản phẩm, mục tiêu và nền tảng |
| **Cài đặt** | Giao diện, hành vi Chat, mặc định AI, xuất dữ liệu, mật khẩu và phiên đăng nhập |

Menu tài khoản cho phép mở **Hồ sơ cá nhân**, **Cài đặt** và **Đăng xuất**.

## 4. Chat và tạo nội dung quảng cáo

### 4.1. Tạo và quản lý cuộc hội thoại

Trong Chat:

- Chọn **Cuộc hội thoại mới** để bắt đầu một luồng riêng.
- Chọn một cuộc hội thoại trong thanh bên để mở lại lịch sử.
- Tìm kiếm cuộc hội thoại theo tiêu đề.
- Ghim cuộc hội thoại quan trọng.
- Đổi tên, xóa cuộc hội thoại hoặc xóa toàn bộ tin nhắn trong menu của cuộc hội thoại.
- Xuất lịch sử cuộc hội thoại theo định dạng đã chọn hoặc chọn định dạng ngay trong menu xuất.

Tiêu đề cuộc hội thoại có thể được hệ thống tạo tự động từ nội dung trao đổi. Bản nháp đang nhập được lưu cục bộ theo từng cuộc hội thoại để hạn chế mất dữ liệu khi tải lại trang.

### 4.2. Nhập yêu cầu tự nhiên

Nhập yêu cầu vào ô soạn thảo, ví dụ:

> Viết một bài quảng cáo Facebook cho cà phê rang xay, hướng tới nhân viên văn phòng 25–35 tuổi, giọng gần gũi, có CTA dùng thử.

Nhấn **Enter** để gửi; dùng **Shift + Enter** để xuống dòng. Khi AI đang sinh nội dung, nhấn nút dừng để hủy stream hiện tại.

Nút micro cho phép nhập bằng giọng nói nếu trình duyệt hỗ trợ Web Speech API. Lần đầu sử dụng, hãy cấp quyền microphone cho trình duyệt.

### 4.3. Brief thông tin quảng cáo

Chọn biểu tượng **Thông tin quảng cáo** cạnh ô nhập để mở brief có cấu trúc. Các trường gồm:

- **Sản phẩm**: tên sản phẩm/dịch vụ.
- **Nền tảng**: Facebook, TikTok, Instagram, Shopee, Google Ads hoặc **Khác**.
- **Tên nền tảng khác**: bắt buộc khi chọn Khác, ví dụ `Zalo OA`.
- **Mô tả**: tính năng, lợi ích và điểm khác biệt.
- **Khách hàng mục tiêu**: độ tuổi, nhu cầu, hành vi.
- **Mục tiêu quảng cáo**: nhận diện thương hiệu, tăng tương tác, thu hút khách hàng tiềm năng, tăng chuyển đổi/bán hàng hoặc tăng lượt truy cập.
- **Giọng văn**: chuyên nghiệp, gần gũi, trẻ trung, cao cấp, hài hước hoặc thuyết phục.
- **Độ dài**: ngắn, trung bình hoặc dài.
- **Từ khóa**: từ khóa bắt buộc hoặc nên xuất hiện.
- **CTA**: hành động mong muốn ở cuối nội dung.
- **Ngôn ngữ**: Tiếng Việt, English, 日本語 hoặc 한국어.

Chọn **Áp dụng** để gắn brief vào yêu cầu tiếp theo. Các giá trị mặc định được lấy từ **Cài đặt → Tùy chọn AI**.

### 4.4. Nền tảng và thương hiệu

- Bộ chọn nền tảng trong thanh công cụ Chat cho phép đổi nhanh kênh xuất bản.
- Nếu chọn **Khác**, nhập tên kênh/nơi đăng từ 2 đến 80 ký tự.
- Bộ chọn thương hiệu dùng để áp dụng hồ sơ thương hiệu cho cuộc hội thoại hiện tại.
- Có thể đổi thương hiệu mặc định trong **Hồ sơ thương hiệu** hoặc chọn lại trực tiếp trong Chat.

### 4.5. Đính kèm tệp

Chọn biểu tượng kẹp giấy để đính kèm tối đa 5 tệp trong một lần gửi:

- Hình ảnh: PNG, JPG/JPEG, WEBP, tối đa 10 MB mỗi tệp.
- Tài liệu: PDF, DOCX, TXT, tối đa 10 MB mỗi tệp.
- Video: MP4, MOV, WEBM, tối đa 50 MB mỗi tệp.

Tệp DOCX hiện được lưu cùng yêu cầu nhưng chưa được AI đọc nội dung tự động. Chỉ tải lên tệp mà bạn có quyền sử dụng và không đưa dữ liệu bí mật nếu môi trường triển khai chưa được phê duyệt cho dữ liệu đó.

### 4.6. Mẫu quảng cáo trong Chat

Từ **Mẫu quảng cáo**, chọn **Dùng mẫu** để chuyển sang Chat. Mẫu có thể điền sẵn nền tảng, brief và prompt. Nếu ô soạn thảo đang có nội dung chưa gửi, hệ thống hỏi bạn muốn:

- Hủy thao tác.
- Giữ nội dung hiện tại và chỉ áp dụng cài đặt mẫu.
- Thay thế nội dung bằng prompt của mẫu.

## 5. Thao tác trên phản hồi AI

Các nút dưới phản hồi của AI có các chức năng sau:

| Thao tác | Cách dùng |
| --- | --- |
| **Sao chép** | Đưa toàn bộ phản hồi vào clipboard |
| **Chỉnh sửa** | Mở phản hồi trong Content Editor |
| **Đánh giá** | Chấm điểm và hiển thị điểm mạnh, điểm cần cải thiện, bản sửa gợi ý |
| **Tạo A/B** | Tạo ba hướng biến thể để so sánh |
| **Voiceover** | Chuyển kịch bản thành file âm thanh |
| **Kiểm tra thương hiệu** | So khớp nội dung với hồ sơ thương hiệu đang chọn |
| **Lưu** | Lưu hoặc bỏ lưu phản hồi trong Thư viện |
| **Phiên bản khác** | Yêu cầu AI tạo lại một phương án khác |
| **Menu thêm** | Viết ngắn hơn, dài hơn, chuyên nghiệp hơn, thân thiện hơn, thêm/bớt emoji |

### 5.1. Đánh giá chất lượng

Kết quả đánh giá gồm điểm tổng thể, các tiêu chí chất lượng, điểm mạnh, đề xuất cải thiện và bản sửa gợi ý. Điểm số là công cụ hỗ trợ biên tập, không thay thế việc kiểm chứng claim, giá, ưu đãi hoặc thông tin pháp lý.

### 5.2. Tạo biến thể A/B/C

Hệ thống tạo ba hướng thường dùng:

- **A – Lợi ích**: nhấn mạnh giá trị và lợi ích sản phẩm.
- **B – Giá/ưu đãi**: chỉ dùng dữ kiện giá hoặc ưu đãi có trong brief.
- **C – Cảm xúc**: nhấn mạnh cảm xúc hoặc vấn đề của khách hàng.

Trong cửa sổ biến thể, người dùng có thể đánh giá từng bản, bật so sánh, chọn bản chính và lưu bản được chọn vào Thư viện.

### 5.3. Kiểm tra thương hiệu

Chọn một thương hiệu trước khi dùng chức năng này. Kết quả giúp nhận biết mức độ phù hợp về giọng điệu, từ khóa, CTA và các từ bị cấm. Đây là kiểm tra hỗ trợ biên tập; người dùng vẫn cần đọc lại nội dung trước khi xuất bản.

## 6. Voice Studio và voiceover

Từ một phản hồi AI, chọn **Voiceover** để mở Voice Studio:

1. Xác nhận hoặc chỉnh sửa lời thoại, tối đa 10.000 ký tự.
2. Chọn giọng đọc được cung cấp, ví dụ Hoài My hoặc Nam Minh.
3. Điều chỉnh tốc độ từ 0,8x đến 1,5x.
4. Chọn **Tạo Voiceover**.
5. Nghe thử file, xem thời lượng và tải audio xuống.

Nếu mở Voice Studio từ nội dung có tệp/kịch bản, hệ thống có thể hỗ trợ làm sạch hoặc trích xuất kịch bản trước khi tạo audio. Hãy kiểm tra lại văn bản sau khi làm sạch vì tên riêng, số liệu và ký hiệu có thể cần sửa thủ công.

## 7. Media Studio: ảnh và video

Mở **Media Studio** từ tiêu đề Chat. Asset được gắn với conversation hiện tại; mỗi lần chỉnh sửa tạo version mới và không ghi đè bản gốc.

### 7.1. Tạo ảnh quảng cáo

1. Chọn tab **Ảnh**.
2. Nhập mô tả sản phẩm, bối cảnh, phong cách và thông điệp.
3. Chọn tỷ lệ: 1:1, 4:5, 9:16, 16:9, 3:2 hoặc 2:3.
4. Có thể tải ảnh tham chiếu PNG/JPG/WEBP.
5. Chọn **Tạo ảnh**.
6. Xem preview, chọn asset làm nguồn cho lần chỉnh sửa tiếp theo hoặc tải xuống.

Ảnh đã tạo được hiển thị trong thư viện ảnh của conversation. Có thể xóa asset ảnh sau khi xác nhận; thao tác xóa không thể khôi phục từ giao diện.

### 7.2. Tạo video bằng AI

1. Chọn tab **Video** và khu vực **Tạo video bằng AI**.
2. Nhập prompt video.
3. Chọn tỷ lệ ngang 16:9 hoặc dọc 9:16.
4. Chọn ảnh tham chiếu nếu muốn.
5. Thời lượng giao diện hiện hỗ trợ 8 giây.
6. Chọn **Tạo video AI** và theo dõi trạng thái job.

> Tạo video AI phụ thuộc provider, API key, quota và quyền truy cập của môi trường triển khai. Trạng thái có thể là đang xử lý, hoàn tất hoặc thất bại; không coi một job mock/test là bằng chứng provider thật đã sẵn sàng.

### 7.3. Chỉnh sửa video kỹ thuật

Tải video MP4/MOV/WEBM lên hoặc chọn video đã có trong conversation. Các operation hiện có:

- Cắt video theo thời điểm bắt đầu/kết thúc.
- Đổi tỷ lệ hoặc crop: 16:9, 9:16, 1:1, 4:5.
- Thêm text overlay.
- Thêm CTA overlay.
- Thêm phụ đề theo từng đoạn thời gian.
- Điều chỉnh âm lượng từ 0 đến 4.
- Tắt tiếng.
- Ghép từ hai video trở lên.

Chọn **Tạo version video** để tạo bản mới. Việc xử lý thực tế còn phụ thuộc FFmpeg/FFprobe và cấu hình runtime.

### 7.4. Chỉnh sửa video bằng hội thoại

1. Chọn một video hoàn tất trong thư viện.
2. Nhập yêu cầu tự nhiên, ví dụ: “Cắt 5 giây đầu, đổi sang 9:16 và thêm CTA ở cuối”.
3. Chọn **Phân tích kế hoạch**.
4. Kiểm tra danh sách operation mà hệ thống đề xuất.
5. Chọn **Thực thi kế hoạch**.
6. Xem trạng thái, preview hoặc tải các version đã tạo.

AI chỉ chuyển yêu cầu thành kế hoạch operation được cho phép; không nhập lệnh hệ điều hành hoặc đường dẫn filesystem tùy ý vào yêu cầu.

## 8. Thư viện nội dung

Mở **Thư viện** để quản lý các phản hồi hoặc biến thể đã lưu:

- Tìm theo tiêu đề hoặc nội dung.
- Mở modal để xem nội dung Markdown.
- Sao chép nội dung.
- Mở trong Content Editor.
- Xóa nội dung đã lưu.

Nội dung trong Thư viện vẫn tồn tại khi xóa liên kết khỏi một chiến dịch. Xóa hồ sơ thương hiệu cũng không xóa các nội dung đã lưu; chỉ bỏ liên kết thương hiệu.

## 9. Content Editor

Mở Editor bằng nút **Chỉnh sửa** từ phản hồi Chat hoặc Thư viện.

### 9.1. Trường chỉnh sửa

- Trạng thái: Bản nháp, Sẵn sàng hoặc Lưu trữ.
- Nền tảng và tên nền tảng khác.
- Thương hiệu.
- Tiêu đề.
- Nội dung chính, có hỗ trợ Markdown.
- CTA.
- Hashtag.
- Ghi chú nội bộ; ghi chú này không được đưa vào nội dung xuất.
- Chiến dịch liên kết và tùy chọn đặt làm nội dung chính của chiến dịch.

### 9.2. Lưu và quản lý phiên bản

- **Lưu**: lưu bản nháp hiện tại.
- **Lưu thành phiên bản mới**: ghi lại version cùng tóm tắt thay đổi.
- **Hoàn tác**: bỏ thay đổi chưa lưu trên thiết bị.
- **Lịch sử phiên bản**: xem, sao chép, xuất, so sánh hoặc khôi phục version.
- **Khôi phục**: đưa version cũ thành nội dung hiện tại và tạo version mới; các version sau đó vẫn được giữ.

Nếu đóng Editor khi còn thay đổi chưa lưu, chọn tiếp tục sửa, bỏ thay đổi và đóng, hoặc lưu rồi đóng. Nếu phát hiện bản nháp cục bộ mới hơn server, chọn dùng bản server hoặc khôi phục bản nháp cục bộ.

### 9.3. AI Rewrite

Chọn một đoạn trong nội dung rồi mở **AI Rewrite**. Có thể yêu cầu AI:

- Viết lại đoạn được chọn.
- Thay toàn bộ nội dung.
- Bổ sung nội dung ở cuối.
- Tạo tiêu đề mới.
- Cải thiện CTA.
- Thêm hashtag.

Đề xuất AI chỉ được áp dụng vào bản nháp; cần bấm lưu để ghi vào server.

## 10. Mẫu quảng cáo

Trong **Mẫu quảng cáo**, người dùng có thể:

- Tìm theo từ khóa.
- Lọc theo nền tảng, danh mục và phạm vi mẫu hệ thống/cá nhân.
- Xem mẫu phổ biến và mẫu yêu thích.
- Yêu thích hoặc bỏ yêu thích.
- Dùng mẫu để mở Chat.
- Tạo mẫu cá nhân.
- Chỉnh sửa hoặc xóa mẫu cá nhân.
- Sao chép một mẫu có sẵn thành mẫu của mình.

Khi tạo/chỉnh sửa mẫu, có thể khai báo nội dung nguồn đã lưu, tiêu đề, nền tảng, tên nền tảng khác, mô tả, danh mục, CTA gợi ý, giọng văn mặc định, độ dài và prompt template.

Mẫu hệ thống không bị xóa khỏi hệ thống của người dùng. Chức năng xóa chỉ áp dụng cho mẫu cá nhân.

## 11. Hồ sơ thương hiệu

Chọn **Hồ sơ thương hiệu → Tạo hồ sơ** và khai báo:

- Thông tin cơ bản: tên, ngành nghề, website, slogan, mô tả.
- Định hướng: sứ mệnh, khách hàng mục tiêu, tính cách, giọng điệu, ngôn ngữ.
- Nhận diện: màu chính, màu phụ.
- Quy chuẩn nội dung: từ khóa ưu tiên, từ ngữ không được dùng, CTA ưu tiên và writing guidelines.
- Đánh dấu hồ sơ mặc định.

Trên từng thẻ thương hiệu có thể xem chi tiết, chỉnh sửa, đặt mặc định hoặc xóa. Chi tiết thương hiệu hiển thị thống kê chiến dịch, nội dung đã lưu, điểm nhất quán trung bình và nền tảng nổi bật.

### 11.1. Tài sản thương hiệu

Trong chi tiết thương hiệu, chọn **Tải tệp** để thêm logo, ảnh hoặc tài liệu tham chiếu. Định dạng hỗ trợ gồm PNG, JPG/JPEG, WEBP, PDF, DOCX và TXT; mỗi tệp tối đa 10 MB. Có thể tải xuống hoặc xóa từng asset.

### 11.2. Áp dụng thương hiệu

Chọn thương hiệu trong Chat hoặc Content Editor trước khi tạo/kiểm tra nội dung. AI dùng hồ sơ làm ngữ cảnh để giữ giọng điệu và quy chuẩn, nhưng người dùng vẫn phải kiểm tra nội dung trước khi xuất bản.

## 12. Chiến dịch

### 12.1. Tạo và lọc chiến dịch

Chọn **Chiến dịch → Tạo chiến dịch**, sau đó nhập:

- Tên chiến dịch.
- Tên sản phẩm.
- Nền tảng và tên nền tảng khác.
- Trạng thái: Bản nháp, Đang chạy, Hoàn thành hoặc Lưu trữ.
- Thương hiệu.
- Mục tiêu.
- Khách hàng mục tiêu.
- Mô tả và ghi chú nội bộ.

Danh sách chiến dịch có thể lọc theo từ khóa, trạng thái và nền tảng. Mỗi chiến dịch có thể chỉnh sửa hoặc xóa.

### 12.2. Quản lý nội dung trong chiến dịch

1. Mở chi tiết chiến dịch.
2. Chọn **Thêm từ Thư viện**.
3. Chọn một hoặc nhiều nội dung đã lưu.
4. Xem, sao chép, đánh giá, tạo A/B, xuất hoặc xóa liên kết.
5. Chọn một nội dung làm **phiên bản chính**.

Xóa nội dung khỏi chiến dịch chỉ xóa liên kết; nội dung gốc trong Thư viện vẫn được giữ.

## 13. Dashboard

Dashboard hiển thị:

- Tổng số cuộc hội thoại.
- Tổng nội dung đã tạo và số nội dung trong 7 ngày gần nhất.
- Tổng nội dung đã lưu.
- Số lần đánh giá.
- Số biến thể A/B.
- Nền tảng sử dụng nhiều nhất và số nội dung trong 30 ngày.
- Biểu đồ hoạt động theo ngày.
- Biểu đồ phân bổ theo nền tảng.

Nếu chưa có nội dung được tạo, Dashboard hiển thị trạng thái trống và hướng dẫn bắt đầu từ Chat.

## 14. Hồ sơ cá nhân và Cài đặt

### 14.1. Hồ sơ cá nhân

Trong **Hồ sơ cá nhân** có thể:

- Đổi username và email.
- Tải ảnh đại diện JPG, PNG hoặc WEBP, tối đa 5 MB.
- Xóa ảnh đại diện.
- Xem ngày tham gia.
- Xem thống kê hội thoại, nội dung đã lưu, chiến dịch và nền tảng phổ biến.

Username và email phải duy nhất trong hệ thống.

### 14.2. Giao diện

Chọn một trong các chế độ **Sáng**, **Tối** hoặc **Hệ thống**. Lựa chọn được áp dụng cho toàn ứng dụng và lưu ở trình duyệt.

### 14.3. Tùy chọn Chat

Có thể bật/tắt:

- Tự động cuộn theo phản hồi AI.
- Hiển thị thời gian dưới tin nhắn.
- Xác nhận trước khi xóa.
- Tự mở cuộc hội thoại gần nhất khi vào Chat.

### 14.4. Tùy chọn AI

Thiết lập mặc định cho nền tảng, tên nền tảng khác, giọng văn, ngôn ngữ và độ dài. Các giá trị này được dùng để điền nhanh vào brief mới.

### 14.5. Xuất dữ liệu

Chọn định dạng mặc định Markdown, Text hoặc PDF. Có thể bật **Kèm thời gian tin nhắn** khi xuất lịch sử hội thoại.

### 14.6. Phiên đăng nhập

Trong phần phiên hoạt động, xem các thiết bị/phiên đang đăng nhập, đăng xuất từng phiên hoặc đăng xuất khỏi tất cả thiết bị. Nếu nghi ngờ token bị lộ, đổi mật khẩu và đăng xuất tất cả phiên.

## 15. Nguyên tắc sử dụng AI an toàn

- Kiểm tra lại giá, phần trăm giảm giá, chứng nhận, số liệu, claim và thông tin pháp lý trước khi đăng.
- AI không được tự bịa dữ kiện nếu brief không cung cấp; người dùng vẫn chịu trách nhiệm về thông tin đưa vào quảng cáo.
- Không đưa API key, mật khẩu, dữ liệu cá nhân nhạy cảm hoặc tài liệu mật vào prompt/tệp đính kèm nếu chưa có chính sách bảo vệ phù hợp.
- Không xem điểm đánh giá AI là kiểm duyệt pháp lý hoặc kiểm chứng sự thật.
- Sử dụng tài sản hình ảnh, video, âm thanh và font mà người dùng có quyền sử dụng.
- Không xóa asset media hoặc nội dung quan trọng trước khi đã tải bản sao cần thiết.

## 16. Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không đăng nhập được | Kiểm tra email/username, mật khẩu, trạng thái backend và kết nối mạng |
| Không nhận OTP | Kiểm tra Spam, email cấu hình SMTP và thời gian chờ gửi lại |
| Google Login bị vô hiệu hóa | Kiểm tra `GOOGLE_CLIENT_ID` và `VITE_GOOGLE_CLIENT_ID` |
| Chat không trả lời | Kiểm tra backend, `GEMINI_API_KEY`, quota và console/network của trình duyệt |
| Không tải được tệp | Kiểm tra phần mở rộng, MIME, kích thước và giới hạn 5 tệp |
| Không xem được media | Kiểm tra asset đã hoàn tất chưa, quyền sở hữu và storage persistent |
| Video AI thất bại | Kiểm tra provider Veo, quyền truy cập, quota và trạng thái job |
| Chỉnh video không chạy | Kiểm tra FFmpeg/FFprobe trong runtime backend |
| Mất file sau redeploy | Kiểm tra persistent disk hoặc chuyển sang object storage |
| Route bị 404 sau refresh | Cấu hình SPA fallback về `index.html` cho frontend hosting |

## 17. Ma trận chức năng hiện tại

| Nhóm | Chức năng |
| --- | --- |
| Tài khoản | Đăng ký, đăng nhập local, Google Login tùy chọn, xác minh email, quên/đặt lại mật khẩu OTP, đổi mật khẩu, quản lý phiên, đăng xuất |
| Chat | CRUD hội thoại, tìm kiếm, ghim, đổi tên, xóa, xóa tin nhắn, stream, dừng sinh, sửa prompt và sinh lại phản hồi |
| Brief | Sản phẩm, mô tả, khách hàng, mục tiêu, nền tảng, tone, ngôn ngữ, độ dài, từ khóa, CTA |
| Nội dung | Sao chép, lưu, đánh giá, cải thiện, tạo A/B/C, kiểm tra thương hiệu, voiceover, xuất |
| Tệp | Đính kèm ảnh/video/PDF/DOCX/TXT, kiểm tra loại/kích thước/quyền sở hữu |
| Media | Tạo ảnh, ảnh tham chiếu, tạo video AI, upload video, chỉnh video kỹ thuật, chỉnh bằng hội thoại, version, preview, download |
| Thư viện | Tìm kiếm, xem, sao chép, sửa, xóa nội dung đã lưu |
| Editor | Markdown, CTA, hashtag, ghi chú, status, platform, brand, campaign, AI rewrite, lưu version, so sánh, khôi phục, xuất |
| Mẫu | Lọc, yêu thích, dùng mẫu, tạo/sửa/xóa mẫu cá nhân, clone mẫu |
| Thương hiệu | CRUD, đặt mặc định, asset, thống kê, kiểm tra nhất quán |
| Chiến dịch | CRUD, lọc, liên kết nội dung, đặt nội dung chính, trạng thái |
| Phân tích | Summary, activity theo ngày, platform usage |
| Cá nhân hóa | Hồ sơ, avatar, theme, cài đặt Chat, mặc định AI, định dạng xuất, session |

## 18. Ghi chú triển khai

Tài liệu này mô tả cách dùng giao diện và hành vi theo source hiện tại. Một số chức năng phụ thuộc cấu hình môi trường:

- Tạo text và stream phụ thuộc Gemini API.
- Google Login phụ thuộc Google OAuth.
- OTP phụ thuộc SMTP.
- Voiceover phụ thuộc provider TTS.
- Tạo ảnh/video phụ thuộc provider media, quota và storage.
- Chỉnh sửa video thực tế phụ thuộc FFmpeg/FFprobe.
- File upload cần persistent disk hoặc object storage khi triển khai lâu dài.

Khi thay đổi route, label, giới hạn file, provider hoặc nghiệp vụ, cần cập nhật tài liệu này cùng với [docs/07-quy-uoc-dong-bo-tai-lieu.md](./07-quy-uoc-dong-bo-tai-lieu.md).

## Ghi chu cap nhat giao dien — 05/10/2026

- Giao dien co che do Sang, Toi va He thong; dark mode da duoc dong bo lai theo he mau xanh navy-indigo/tim nhe.
- Nut `New Chat` va nut tao hoi thoai moi tren header su dung mau pastel nhat hon, voi hover cung he mau.
- Header Chat khong con duong ke ngang xanh ro; phan ngan cach duoc lam mem bang nen pha tron.
- Cac card, sidebar, input, modal, chu phu va trang thai hover trong dark mode duoc dieu chinh de cung bang mau.
- Day la thay doi presentation/UI, khong thay doi cach tao noi dung, API, luu hoi thoai hoac cac chuc nang Chat.
