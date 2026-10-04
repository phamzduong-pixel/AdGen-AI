# Kế hoạch phát triển AdGen Trend Radar

> Trạng thái: đề xuất trước triển khai  
> Phiên bản kế hoạch: 04/10/2026  
> Phạm vi: mở rộng AdGen AI thành hệ thống tìm kiếm, kiểm chứng xu hướng và chuyển hóa xu hướng thành chiến dịch quảng cáo.

## 1. Tầm nhìn

AdGen AI không chỉ tạo nội dung quảng cáo bằng AI mà còn hỗ trợ người dùng trả lời được các câu hỏi:

- Thị trường và người dùng đang quan tâm điều gì?
- Xu hướng đó xuất hiện trên nền tảng nào, ở khu vực nào và trong khoảng thời gian nào?
- Vì sao sản phẩm hoặc chủ đề đó được chú ý?
- Nguồn thông tin ở đâu, thời điểm cập nhật là khi nào và độ tin cậy ra sao?
- Có thể biến thông tin này thành quảng cáo hoặc chiến dịch nào?
- Sản phẩm có thông tin chưa đủ chắc chắn hoặc tuyên bố nào cần cảnh báo không?

Tên đề xuất cho module là **AdGen Trend Radar – phát hiện xu hướng và biến xu hướng thành chiến dịch quảng cáo có nguồn dẫn chứng**.

### Định vị trong toàn hệ thống

Trend Radar chỉ là một năng lực bổ trợ bên trong AdGen AI, không biến AdGen AI thành công cụ tìm kiếm thông tin tổng quát. Hệ thống chỉ kích hoạt việc tra cứu khi yêu cầu của người dùng có liên quan, chẳng hạn như hỏi về xu hướng mới, sản phẩm đang nổi, thông tin cập nhật, nguồn dẫn chứng hoặc kiểm tra độ tin cậy sản phẩm trước khi quảng cáo.

Với các yêu cầu tạo quảng cáo thông thường, hệ thống tiếp tục sử dụng luồng AdGen AI hiện tại và không tự động gọi nguồn bên ngoài. Kết quả tra cứu, nếu có, chỉ được đưa vào brief, nội dung hoặc campaign khi nó phục vụ trực tiếp cho yêu cầu quảng cáo.

## 2. Hiện trạng và khoảng trống

AdGen AI đã có nền tảng để mở rộng tính năng này:

- Có lớp `TrendIntelligenceService`, bộ kiểm tra độ mới và độ tin cậy của dữ liệu.
- Có giao diện collector để bổ sung các nguồn như Google Trends, TikTok, RSS hoặc nguồn dữ liệu thị trường.
- Có lớp thông tin tĩnh về đặc điểm, định dạng và quy tắc quảng cáo của từng nền tảng.
- Có luồng AI, brand profile, template, content library và campaign để sử dụng kết quả sau phân tích.

Khoảng trống hiện tại:

- Chưa có collector kết nối dữ liệu xu hướng trực tuyến thực tế.
- Chưa có kho lưu bằng chứng gồm URL, thời gian thu thập, nội dung trích yếu và trạng thái xác minh.
- Chưa có cơ chế nhận diện khi nào câu hỏi cần tra cứu bên ngoài và khi nào chỉ cần dùng luồng tạo quảng cáo hiện tại.
- Chưa có khu vực kết quả tra cứu tích hợp trong Chat/brief/campaign để người dùng xem nguồn liên quan mà không tách AdGen AI thành công cụ search độc lập.
- Chưa có cơ chế tự động phân biệt thông tin đã xác minh, ý kiến cộng đồng và suy luận của AI.
- Chưa có lịch cập nhật, xử lý dữ liệu cũ hoặc cảnh báo khi các nguồn mâu thuẫn.

Vì vậy, đây là kế hoạch mở rộng có thể tích hợp vào kiến trúc hiện tại, không phải thay thế toàn bộ hệ thống.

## 3. Nguyên tắc thiết kế

### 3.1. Evidence-first

AI chỉ được phân tích và tạo nội dung dựa trên dữ liệu đã thu thập. Mỗi nhận định quan trọng phải có nguồn tham chiếu hoặc được ghi rõ là suy luận.

### 3.2. API chính thức trước

Ưu tiên API và trang dữ liệu chính thức của nền tảng. Chỉ dùng công cụ tìm kiếm, RSS hoặc đọc URL công khai khi API không phù hợp. Việc thu thập dữ liệu phải tôn trọng quyền truy cập, điều khoản sử dụng, giới hạn tốc độ và quyền riêng tư.

### 3.3. Nhiều nguồn để đối chiếu

Một video hoặc một bài đăng chưa đủ để kết luận một xu hướng. Hệ thống cần so sánh nhiều tín hiệu như lượng tìm kiếm, mức độ xuất hiện, quảng cáo, tin tức, thảo luận và tính lặp lại theo thời gian.

### 3.4. Minh bạch về mức độ chắc chắn

Kết quả phải thể hiện rõ:

- Đã xác minh.
- Có bằng chứng nhưng chưa đầy đủ.
- Là nhận định hoặc thảo luận của cộng đồng.
- Là suy luận của AI.
- Có nguồn mâu thuẫn hoặc chưa đủ dữ liệu.

### 3.5. An toàn khi nói về sản phẩm

Đặc biệt với mỹ phẩm, thực phẩm, thực phẩm chức năng, y tế và sản phẩm ảnh hưởng đến sức khỏe, hệ thống không được tự biến lời quảng cáo thành công dụng đã được chứng minh. Khi thiếu thông tin về thành phần, nguồn gốc, chứng nhận hoặc hướng dẫn sử dụng, hệ thống phải cảnh báo và hạn chế tuyên bố mạnh.

## 4. Luồng xử lý đề xuất

```text
Người dùng nhập yêu cầu
        ↓
Query Planner phân tích sản phẩm, nền tảng, khu vực, ngôn ngữ, khoảng thời gian
        ↓
Source Router chọn nguồn phù hợp
        ↓
API chính thức / Search API / RSS / URL người dùng cung cấp
        ↓
Chuẩn hóa, loại trùng, kiểm tra thời gian và nguồn
        ↓
Evidence Store lưu dẫn chứng gốc
        ↓
Trend Analyzer chấm điểm tín hiệu và phát hiện xu hướng
        ↓
Product Trust Analyzer kiểm tra công dụng, tuyên bố và lỗ hổng thông tin
        ↓
Report Builder tạo báo cáo có trích dẫn và cảnh báo
        ↓
Campaign Planner chuyển kết quả thành brief, nội dung và chiến dịch
```

Trước khi gọi Query Planner, hệ thống cần có một **Intent Router**. Router xác định yêu cầu có cần dữ liệu mới hoặc nguồn bên ngoài hay không. Nếu không cần, yêu cầu đi thẳng vào luồng AdGen AI hiện tại; nếu cần, mới kích hoạt Query Planner và các collector.

Việc tra cứu có thể được kích hoạt khi người dùng dùng các cụm như “mới nhất”, “đang hot”, “trên TikTok”, “tìm nguồn”, “kiểm tra thông tin”, hoặc khi brief cần dữ liệu thị trường hiện tại. Khi tự suy ra nhu cầu tra cứu từ brief, hệ thống nên thông báo rõ cho người dùng trước khi lấy dữ liệu.

## 5. Chiến lược nguồn dữ liệu

| Nhóm nguồn | Mục đích | Cách dùng dự kiến |
| --- | --- | --- |
| API chính thức | Lấy dữ liệu nền tảng có cấu trúc | Collector riêng cho từng nền tảng, có khóa API và giới hạn quota |
| Công cụ tìm kiếm web | Tìm bài viết, báo cáo, website sản phẩm và tin tức | Gửi truy vấn có bộ lọc miền, thời gian và ngôn ngữ |
| URL do người dùng nhập | Phân tích nguồn cụ thể | Đọc nội dung công khai, lưu URL và thời điểm truy cập |
| RSS/public feed | Theo dõi nguồn cập nhật thường xuyên | Đồng bộ theo lịch, loại trùng theo URL và nội dung |
| Nguồn thủ công đã xác minh | Bổ sung dữ liệu trong giai đoạn MVP | Cho phép người quản trị nhập và xác nhận dữ liệu |

Các nguồn có thể nghiên cứu khi triển khai:

- Google Trends API để tham khảo mức độ quan tâm tìm kiếm; quyền truy cập và trạng thái API cần được kiểm tra tại thời điểm tích hợp.
- YouTube Data API để thu thập thông tin video, kênh, chủ đề và chỉ số công khai.
- Meta Ad Library để tham khảo quảng cáo đang được công khai.
- TikTok Creative Center hoặc nguồn TikTok được cho phép theo quyền truy cập và điều khoản hiện hành.
- Công cụ tìm kiếm web như Bing Web Search, Google Programmable Search, Tavily, SerpAPI hoặc dịch vụ tương đương.

Nguồn tham khảo chính thức: [Google Trends API](https://developers.google.com/search/apis/trends), [YouTube Data API](https://developers.google.com/youtube/v3/docs), [Meta Ad Library](https://www.facebook.com/ads/library/), [TikTok Creative Center](https://ads.tiktok.com/business/creativecenter/).

## 6. Các thành phần cần xây dựng

### 6.1. Query Planner

Chuyển yêu cầu tự nhiên thành các tham số có cấu trúc:

- Sản phẩm hoặc chủ đề.
- Nền tảng cần tra cứu.
- Quốc gia, khu vực và ngôn ngữ.
- Khoảng thời gian.
- Loại dữ liệu cần tìm: xu hướng, quảng cáo, đánh giá, công dụng hoặc tin tức.
- Mức độ nghiêm ngặt của nguồn.

### 6.2. Source Router và Collector

Router chọn collector dựa trên yêu cầu. Các collector dự kiến:

- `OfficialPlatformCollector`.
- `GoogleTrendsCollector`.
- `YouTubeCollector`.
- `MetaAdLibraryCollector`.
- `TikTokCollector` khi có quyền truy cập phù hợp.
- `WebSearchCollector`.
- `UrlSourceCollector`.
- `RssCollector`.
- `ManualVerifiedCollector`.

Collector không được tự tạo số liệu. Nếu nguồn không trả dữ liệu, hệ thống phải trả trạng thái thiếu dữ liệu thay vì suy đoán.

### 6.3. Evidence Store

Mỗi bằng chứng nên lưu tối thiểu:

- URL và tên nguồn.
- Tiêu đề, nội dung trích yếu hoặc đoạn dẫn chứng.
- Nhà xuất bản hoặc chủ sở hữu nguồn.
- Thời điểm bài viết được đăng nếu có.
- Thời điểm AdGen AI truy cập.
- Nền tảng, khu vực, ngôn ngữ và loại dữ liệu.
- Hash nội dung để phát hiện thay đổi hoặc trùng lặp.
- Mức độ tin cậy và trạng thái xác minh.

### 6.4. Trend Analyzer

Trend Analyzer không chỉ đếm số lần xuất hiện. Nó kết hợp các tín hiệu:

- Mức tăng quan tâm theo thời gian.
- Số lượng video, bài viết, quảng cáo hoặc người sáng tạo tham gia.
- Mức độ lặp lại giữa nhiều nền tảng.
- Tính mới, tốc độ tăng và thời gian duy trì.
- Yếu tố mùa vụ, sự kiện hoặc chương trình khuyến mại.
- Mức độ liên quan với ngành hàng và khách hàng mục tiêu.

Kết quả nên gọi là **tín hiệu cho thấy xu hướng** hoặc **giả thuyết nguyên nhân**, không khẳng định tuyệt đối rằng một tín hiệu là nguyên nhân duy nhất khiến sản phẩm nổi tiếng.

### 6.5. Product Trust Analyzer

Thông tin sản phẩm được chia thành các lớp:

1. **Thông tin đã xác minh**: đến từ website thương hiệu, nhãn sản phẩm, tài liệu kỹ thuật, cơ quan hoặc nguồn chuyên môn phù hợp.
2. **Tín hiệu thị trường**: lượt quan tâm, quảng cáo, đánh giá và thảo luận.
3. **Ý kiến người dùng**: phản hồi hoặc trải nghiệm cá nhân, không đại diện cho bằng chứng khoa học.
4. **Suy luận của AI**: giải thích hoặc gợi ý cần được kiểm tra lại.

Kết quả sản phẩm cần trả lời:

- Sản phẩm là gì?
- Công dụng nào có nguồn hỗ trợ?
- Vì sao sản phẩm có thể đang được chú ý?
- Thông tin nào còn thiếu?
- Có nguồn nào mâu thuẫn không?
- Nội dung quảng cáo nào có nguy cơ gây hiểu lầm?
- Người dùng cần kiểm tra gì trước khi sử dụng hoặc quảng bá?

## 7. Giao diện người dùng dự kiến

### 7.1. Khu vực Trend Radar trong luồng hiện có

Không bắt buộc tạo một sản phẩm search riêng. Trend Radar nên xuất hiện như một panel hoặc bước bổ sung trong Chat, trình tạo brief hoặc campaign. Người dùng nhập:

- Từ khóa hoặc tên sản phẩm.
- Nền tảng muốn theo dõi.
- Khu vực và khoảng thời gian.
- URL nguồn nếu đã có.
- Mục tiêu: nghiên cứu thị trường, kiểm tra sản phẩm hoặc tạo chiến dịch.

### 7.2. Báo cáo kết quả

Báo cáo gồm:

- Tóm tắt xu hướng.
- Điểm xu hướng và các tín hiệu cấu thành điểm.
- Nền tảng và khu vực nổi bật.
- Lý do sản phẩm hoặc chủ đề được chú ý dưới dạng giả thuyết có dẫn chứng.
- Thẻ nguồn, ngày cập nhật và độ tin cậy.
- Thông tin sản phẩm đã xác minh.
- Dữ liệu còn thiếu và cảnh báo rủi ro.
- Nút dùng insight để tiếp tục tạo brief hoặc chiến dịch.
- Nút bỏ qua kết quả và quay lại luồng tạo quảng cáo thông thường.

### 7.3. Trạng thái kết quả

- **Đã xác minh**: có nguồn phù hợp và đủ mới.
- **Cần kiểm tra thêm**: có nguồn nhưng chưa đủ hoặc chỉ có một chiều thông tin.
- **Chưa xác minh**: chủ yếu là thảo luận, quảng cáo hoặc suy luận.
- **Mâu thuẫn**: các nguồn đưa ra thông tin không thống nhất.

## 8. Lộ trình triển khai đề xuất

### Giai đoạn 0 – Thiết kế và chuẩn hóa

- Chốt thuật ngữ, trạng thái tin cậy và tiêu chuẩn nguồn.
- Chốt cấu trúc evidence và cách lưu trích dẫn.
- Chọn nhóm ngành hàng thử nghiệm, ưu tiên nhóm ít rủi ro.
- Xác định API key, quota, chi phí và điều khoản của từng nguồn.

### Giai đoạn 1 – MVP có kiểm soát

- Cho phép người dùng nhập câu hỏi và URL.
- Kết nối một công cụ tìm kiếm web được chọn.
- Đọc nguồn chính thức của thương hiệu và các bài viết công khai.
- Lưu bằng chứng, thời gian truy cập và đường dẫn.
- Tạo báo cáo xu hướng có trích dẫn.
- Cho phép chuyển báo cáo thành brief quảng cáo.

Mục tiêu của MVP là chứng minh được chuỗi giá trị: **tìm kiếm → kiểm chứng → giải thích → tạo quảng cáo**.

### Giai đoạn 2 – Đa nền tảng và cập nhật

- Bổ sung YouTube, Google Trends, Meta Ad Library và nguồn TikTok phù hợp quyền truy cập.
- Chuẩn hóa dữ liệu giữa các nền tảng.
- Thêm lịch cập nhật và cache dữ liệu.
- Phát hiện nguồn trùng, nguồn cũ và nguồn mâu thuẫn.
- Hiển thị so sánh xu hướng giữa các nền tảng.

### Giai đoạn 3 – Product Trust và cảnh báo

- Phân loại công dụng, tuyên bố và bằng chứng sản phẩm.
- Cảnh báo nội dung quảng cáo quá mức hoặc chưa đủ căn cứ.
- Bổ sung chế độ chỉ dùng thông tin đã xác minh.
- Cho phép người dùng đánh dấu nguồn đáng tin hoặc nguồn cần loại bỏ.

### Giai đoạn 4 – Tự động hóa và tối ưu chiến dịch

- Theo dõi xu hướng định kỳ theo ngành hàng.
- Gửi cảnh báo khi xu hướng tăng mạnh hoặc giảm nhanh.
- Đề xuất nhiều góc quảng cáo theo từng nền tảng.
- Theo dõi kết quả chiến dịch và so sánh với tín hiệu xu hướng ban đầu.

## 9. Tiêu chí nghiệm thu trước khi mở rộng

- Mỗi nhận định quan trọng trong báo cáo có ít nhất một nguồn tham chiếu.
- Không có nguồn thì hệ thống ghi rõ “chưa đủ dữ liệu”, không tự tạo số liệu.
- Người dùng mở được URL nguồn từ báo cáo.
- Báo cáo hiển thị thời điểm dữ liệu được cập nhật.
- Dữ liệu cũ, trùng hoặc mâu thuẫn được đánh dấu.
- Nội dung tạo ra phân biệt được thông tin sản phẩm và suy luận quảng cáo.
- Với ngành hàng nhạy cảm, hệ thống tạo cảnh báo trước khi sinh nội dung mạnh.
- Kết quả có thể chuyển thành brief, content hoặc campaign mà vẫn giữ lại liên kết nguồn.
- Khi API lỗi hoặc hết quota, hệ thống vẫn báo trạng thái rõ ràng và không coi dữ liệu cũ là dữ liệu mới.

## 10. Rủi ro và cách xử lý

| Rủi ro | Cách giảm thiểu |
| --- | --- |
| API thay đổi, hết quota hoặc bị giới hạn quyền | Dùng adapter riêng, cache, retry có giới hạn và nguồn dự phòng |
| Website chặn truy cập hoặc thay đổi giao diện | Ưu tiên API, RSS và URL người dùng cung cấp; không phụ thuộc scraping không ổn định |
| Một nguồn tạo cảm giác xu hướng giả | Đối chiếu nhiều nguồn và hiển thị tín hiệu thay vì kết luận tuyệt đối |
| Thông tin sản phẩm sai hoặc thổi phồng | Tách sự thật, ý kiến và suy luận; bắt buộc cảnh báo khi thiếu bằng chứng |
| Dữ liệu không còn mới | Lưu `published_at`, `accessed_at`, thời hạn hiệu lực và trạng thái stale |
| Chi phí tìm kiếm tăng | Giới hạn phạm vi truy vấn, cache, ưu tiên nguồn miễn phí và hiển thị chi phí vận hành |
| Vi phạm điều khoản nền tảng | Kiểm tra quyền truy cập, điều khoản, robots.txt và không thu thập dữ liệu riêng tư |

## 11. Giá trị thực tế và điểm nhấn trình bày

Tính năng này giúp AdGen AI giải quyết một vấn đề thực tế hơn việc chỉ sinh văn bản: người dùng có thể đi từ dữ liệu thị trường đến một quyết định quảng cáo có lý do và nguồn kiểm tra được.

Khi trình bày với thầy cô, có thể nhấn mạnh bốn điểm:

1. Hệ thống kết hợp AI với dữ liệu bên ngoài thay vì chỉ tạo nội dung từ kiến thức có sẵn.
2. Mỗi kết quả có khả năng giải thích và dẫn nguồn.
3. Hệ thống có cơ chế nhận diện giới hạn dữ liệu, không khẳng định khi chưa đủ bằng chứng.
4. Kết quả nghiên cứu được chuyển thành sản phẩm sử dụng được: brief, nội dung, biến thể và chiến dịch.

## 12. Quyết định cần chốt trước khi viết code

- Nguồn dữ liệu đầu tiên của MVP.
- Có sử dụng dịch vụ tìm kiếm trả phí hay chỉ dùng API/public source.
- Nhóm ngành hàng và quốc gia thử nghiệm.
- Tần suất cập nhật dữ liệu.
- Ngưỡng xác minh tối thiểu để tạo quảng cáo.
- Cách lưu trích dẫn và thời hạn giữ dữ liệu.
- Các loại sản phẩm bắt buộc chuyển sang chế độ cảnh báo.
- Người dùng cuối có được tự thêm nguồn hay cần quản trị viên duyệt.

## 13. Ranh giới sản phẩm

Trend Radar không có mục tiêu trở thành công cụ search tổng quát, cho phép tìm mọi chủ đề không liên quan đến quảng cáo hoặc tự động thu thập liên tục mọi nền tảng khi không có yêu cầu. Đây là **retrieval layer theo nhu cầu**, cung cấp dữ liệu mới để nâng chất lượng quyết định và nội dung quảng cáo trong Chat, brief và campaign.

## 14. Phạm vi chưa triển khai trong kế hoạch này

- Chưa kết nối API thật.
- Chưa thay đổi database, backend hoặc frontend.
- Chưa tự động đăng quảng cáo lên các nền tảng.
- Chưa coi số lượt xem hoặc lượt thích là bằng chứng chắc chắn về hiệu quả bán hàng.
- Chưa thay thế kiểm duyệt pháp lý, chuyên gia ngành hàng hoặc trách nhiệm của người dùng đối với nội dung quảng cáo.

Kết luận: hướng **AdGen Trend Radar** khả thi và phù hợp với kiến trúc hiện tại khi được triển khai như một retrieval layer theo ngữ cảnh. Nên bắt đầu bằng MVP tích hợp trong Chat/brief gồm nhận diện nhu cầu tra cứu, tìm kiếm web, nhập URL, lưu bằng chứng và đưa insight trở lại luồng tạo quảng cáo; không xây dựng một công cụ search độc lập.
