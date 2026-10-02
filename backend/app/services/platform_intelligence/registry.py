from app.services.platform_intelligence.models import (
    CtaGuideline,
    ContentStructure,
    HookGuideline,
    PlatformId,
    PlatformSpecification,
)

PLATFORM_SPECIFICATIONS: dict[PlatformId, PlatformSpecification] = {
    PlatformId.FACEBOOK: PlatformSpecification(
        platform_id=PlatformId.FACEBOOK,
        display_name="Facebook Ads & Post",
        primary_objective="Thu hút chú ý khi lướt feed, tạo tương tác (like, cmt, share), kích thích nhắn tin (Messenger) và chuyển đổi mua hàng.",
        audience_behavior="Lướt feed nhanh trên điện thoại, quét tiêu đề/hình ảnh trước khi đọc text, đọc 1-3 dòng đầu trước nút 'Xem thêm'.",
        recommended_tones=["Gần gũi", "Thuyết phục", "Tự nhiên", "Truyền cảm hứng", "Chuyên gia"],
        structure=ContentStructure(
            primary_sections=[
                "Hook mở đầu (1-3 dòng đầu tiên gây tò mò/nêu nỗi đau)",
                "Nội dung chính (PAS / AIDA / FAB kết nối tính năng thành lợi ích)",
                "Ưu đãi & Lý do hành động",
                "Call to Action rõ ràng",
                "Tiêu đề ảnh/banner gợi ý",
                "Hashtag & Bình luận ghim (pinned comment)",
            ],
            suggested_length_guide="Ngắn: 50-90 từ | Trung bình: 120-220 từ | Dài (Storytelling/Deep review): 250-450 từ.",
            key_elements=["Headline banner", "Caption", "CTA Button", "Hashtag", "Pinned comment"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Vấn đề/Nỗi đau", "Lợi ích tức thì", "Câu hỏi gợi mở", "Tình huống thực tế", "Sự thật bất ngờ"],
            time_or_line_constraint="Hiển thị ngay trong 1-3 dòng đầu (trước khi bị cắt 'Xem thêm').",
            examples=[
                "Chạy ads cả tháng nhưng inbox về toàn hỏi giá rồi im lặng?",
                "Tiết kiệm 5 giờ viết content mỗi tuần với quy trình tự động hóa này.",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Nhắn tin tư vấn", "Bình luận nhận ưu đãi", "Xem chi tiết website", "Đặt mua ngay"],
            tone_requirement="Rõ ràng, trực diện, không tạo cảm giác ép buộc hoặc khan hiếm giả tạo.",
            examples=["Nhắn tin ngay để nhận tư vấn chi tiết", "Để lại bình luận 'QUAN TÂM' để nhận bộ tài liệu"],
        ),
        constraints=[
            "Không viết hoa toàn bộ đoạn văn bản.",
            "Không lạm dụng emoji quá mức (dưới 5-7 emoji/bài, trừ bài phong cách trẻ trung).",
            "Không dùng từ ngữ giật tít sai sự thật (clickbait) để tránh vi phạm chính sách Facebook Ads.",
        ],
        best_practices=[
            "Chuyển đổi 100% tính năng kỹ thuật thành lợi ích cuộc sống/công việc của khách hàng.",
            "Đưa ra phương án A/B testing rõ ràng giữa các góc tiếp cận (Angle A: Pain point vs Angle B: Aspirational benefit).",
        ],
        policy_guidelines=[
            "Tuân thủ chính sách quảng cáo Meta: Không cam kết tuyệt đối '100% hết bệnh', không nhắm vào đặc điểm cá nhân nhạy cảm.",
        ],
    ),
    PlatformId.INSTAGRAM: PlatformSpecification(
        platform_id=PlatformId.INSTAGRAM,
        display_name="Instagram Feed, Story & Reels",
        primary_objective="Xây dựng hình ảnh thương hiệu thẩm mỹ (Aesthetic & Visual-first), tăng save/share, dẫn link bio và direct message.",
        audience_behavior="Tập trung thị giác cao, lướt ảnh/Reels nhanh, thích nội dung đẹp mắt, lối sống, truyền cảm hứng và tips ngắn gọn.",
        recommended_tones=["Hiện đại", "Sang trọng", "Trẻ trung", "Truyền cảm hứng", "Tinh tế"],
        structure=ContentStructure(
            primary_sections=[
                "Visual Hook trên ảnh/bìa Carousel/Reels",
                "Caption ngắn gọn, ngắt dòng thoáng",
                "Micro-tips hoặc giá trị cảm xúc",
                "CTA tương tác (Save/Share/DM/Link in Bio)",
                "Bộ Hashtag tối ưu (10-15 thẻ phân tầng)",
            ],
            suggested_length_guide="Feed caption: 80-150 từ | Carousel slide text: 20-40 từ/slide | Story caption: Dưới 30 từ.",
            key_elements=["Visual Concept", "Carousel breakdown", "Clean Caption", "Hashtag Set", "Bio CTA"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Visual text hook trên slide 1", "Aesthetic curiosity", "How-to gọn gàng"],
            time_or_line_constraint="1 dòng đầu tiên của caption và text hiển thị trên cover ảnh.",
            examples=[
                "3 bước tối giản hóa quy trình sáng tạo bạn nên lưu lại ngay.",
                "Góc làm việc gọn gàng bắt đầu từ những chi tiết nhỏ này.",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Lưu bài viết (Save)", "Chia sẻ (Share)", "Nhấp link ở Bio", "Gửi DM"],
            tone_requirement="Thân thiện, gợi mở, khuyến khích lưu trữ giá trị lâu dài.",
            examples=["Lưu lại để áp dụng khi cần", "Link chi tiết mình để ở phần Bio nhé", "Gửi DM cho tụi mình để nhận template"],
        ),
        constraints=[
            "Không để link trần trong caption (Instagram không hỗ trợ click link trong caption).",
            "Đoạn văn ngắt dòng thoáng, không dồn thành khối văn bản đặc.",
        ],
        best_practices=[
            "Luôn đề xuất ý tưởng hình ảnh/carousel slide đi kèm caption.",
            "Tập trung thúc đẩy Save & Share để thuật toán Instagram phân phối tốt hơn.",
        ],
        policy_guidelines=[
            "Tránh spam hashtag lặp đi lặp lại không liên quan đến hình ảnh/nội dung.",
        ],
    ),
    PlatformId.TIKTOK: PlatformSpecification(
        platform_id=PlatformId.TIKTOK,
        display_name="TikTok Video & Ads",
        primary_objective="Thu hút ngay 1-3s đầu, giữ chân người xem hết video, thúc đẩy xu hướng, tương tác bình luận và bấm vào giỏ hàng/link bio.",
        audience_behavior="Tiêu thụ video ngắn dạng lướt dọc liên tục, nghe âm thanh 100%, yêu thích sự chân thực (UGC), nhịp dựng nhanh, ghét quảng cáo lộ liễu.",
        recommended_tones=["Năng động", "Chân thực (UGC)", "Hài hước", "Kịch tính", "Trẻ trung"],
        structure=ContentStructure(
            primary_sections=[
                "Concept & Phong cách video (POV / Review / Story / Tình huống / Trend)",
                "Hook 1-3 giây đầu (Hình ảnh + Âm thanh + Text trên màn hình)",
                "Kịch bản chi tiết theo phân cảnh (Timeline + Visual/Action + Audio/Voice + On-screen Text)",
                "Cao trào & Giải pháp bất ngờ",
                "Call to Action ngắn gọn",
                "Caption TikTok & Bộ Hashtag thịnh hành",
            ],
            suggested_length_guide="Thời lượng tối ưu: 15s - 45s (hoặc 60s cho deep review). Lời thoại: 60 - 150 từ.",
            key_elements=["Video Concept", "Scene-by-scene script", "On-screen text", "Audio cues", "TikTok Caption"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["POV (Điểm nhìn)", "Cảnh báo/Sai lầm thường gặp", "Before/After tức thì", "Câu hỏi gây sốc", "Tiết lộ bí mật"],
            time_or_line_constraint="Phải tạo ấn tượng trong 1 đến 3 giây đầu tiên của video.",
            examples=[
                "Dừng lại 3 giây nếu bạn vẫn đang làm content theo cách thủ công này!",
                "POV: Bạn tìm ra cách x3 năng suất làm việc chỉ sau 1 đêm...",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Nhấp vào giỏ hàng TikTok Shop", "Xem link ở Bio", "Thảo luận ở phần bình luận", "Follow kênh"],
            tone_requirement="Tự nhiên, hối thúc nhẹ nhàng, hòa nhập vào mạch video.",
            examples=["Bấm ngay vào giỏ hàng góc trái bên dưới", "Bạn nghĩ sao về cách này? Bình luận cho mình biết nhé"],
        ),
        constraints=[
            "Lời thoại phải dễ đọc thành tiếng tự nhiên, tránh dùng từ ngữ hàn lâm hoặc quá trang trọng.",
            "Không kéo dài phần mở đầu quá 3 giây.",
        ],
        best_practices=[
            "Phân tách rõ ràng 3 cột: Thời gian - Hành động/Hình ảnh - Lời thoại & Chữ trên màn hình.",
            "Tập trung trải nghiệm người dùng thật (User-Generated Content style).",
        ],
        policy_guidelines=[
            "Tuân thủ chính sách nội dung TikTok: Không sử dụng âm thanh vi phạm bản quyền thương mại nếu chạy ads.",
        ],
    ),
    PlatformId.GOOGLE_ADS: PlatformSpecification(
        platform_id=PlatformId.GOOGLE_ADS,
        display_name="Google Search Ads (RSA)",
        primary_objective="Đón đầu ý định tìm kiếm (High Search Intent), đạt Quality Score cao, tối đa CTR và chuyển đổi trang đích.",
        audience_behavior="Đang chủ động tìm kiếm giải pháp/sản phẩm cụ thể, quét nhanh các dòng tiêu đề trên trang kết quả tìm kiếm Google (SERP).",
        recommended_tones=["Trực diện", "Chuyên nghiệp", "Đáng tin cậy", "Rõ ràng", "Tập trung giải pháp"],
        structure=ContentStructure(
            primary_sections=[
                "Danh sách Tiêu đề (Headlines - Tối đa 30 ký tự mỗi tiêu đề)",
                "Danh sách Đoạn mô tả (Descriptions - Tối đa 90 ký tự mỗi đoạn)",
                "Đề xuất Tiện ích mở rộng (Sitelinks, Callouts, Structured Snippets)",
                "Từ khóa mục tiêu khớp theo ý định tìm kiếm (Exact / Phrase / Broad)",
            ],
            suggested_length_guide="Headlines: <= 30 ký tự/tiêu đề (cung cấp 5-15 options). Descriptions: <= 90 ký tự/mô tả (cung cấp 3-4 options).",
            key_elements=["10-15 Headlines (<=30 chars)", "3-4 Descriptions (<=90 chars)", "Callout Extensions", "Keywords"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Khớp chính xác từ khóa tìm kiếm", "Lợi ích cốt lõi", "Cam kết dịch vụ/Ưu đãi"],
            time_or_line_constraint="30 ký tự đầu tiên trên Headline 1 và Headline 2.",
            examples=[
                "Tạo Content AI Nhanh Chóng",
                "Phần Mềm Marketing Tự Động",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Đăng ký dùng thử", "Nhận báo giá", "Mua ngay", "Liên hệ ngay", "Tìm hiểu thêm"],
            tone_requirement="Dứt khoát, định hướng hành động tìm kiếm rõ ràng.",
            examples=["Dùng Thử Miễn Phí Hôm Nay", "Nhận Báo Giá Ngay Trong 5 Phút"],
        ),
        constraints=[
            "BẮT BUỘC: Headline không vượt quá 30 ký tự (tính cả dấu cách và tiếng Việt).",
            "BẮT BUỘC: Description không vượt quá 90 ký tự (tính cả dấu cách và tiếng Việt).",
            "Không dùng dấu chấm than (!) trên Tiêu đề theo quy định của Google Ads.",
            "Không lặp lại từ khóa spam hoặc viết hoa vô tội vạ.",
        ],
        best_practices=[
            "Phân chia rõ: Tiêu đề chứa từ khóa chính, Tiêu đề nêu lợi ích/USP, Tiêu đề chứa CTA/Ưu đãi.",
            "Đảm bảo thông điệp khớp hoàn hảo với nội dung trên Landing Page.",
        ],
        policy_guidelines=[
            "Không đưa ra cam kết y khoa/tài chính tuyệt đối hoặc nhãn hiệu có bản quyền khi chưa được cấp quyền.",
        ],
    ),
    PlatformId.YOUTUBE: PlatformSpecification(
        platform_id=PlatformId.YOUTUBE,
        display_name="YouTube Video, Shorts & Community",
        primary_objective="Tối ưu thời gian xem (Watch Time) và tỷ lệ giữ chân (Retention), xây dựng uy tín chuyên sâu, tăng Subscribe và chuyển đổi.",
        audience_behavior="Tìm kiếm kiến thức chi tiết, hướng dẫn, giải trí hoặc đánh giá chuyên sâu. Người xem Shorts muốn nắm bắt nội dung chớp nhoáng.",
        recommended_tones=["Chuyên sâu", "Hào hứng", "Kể chuyện (Storytelling)", "Tường minh", "Hài hước vừa vặn"],
        structure=ContentStructure(
            primary_sections=[
                "Tiêu đề (Title) & Ý tưởng Thumbnail (Hình ảnh + Text dưới 5 từ)",
                "Hook giữ chân 5-10 giây đầu (Nêu vấn đề kịch tính + Lời hứa video)",
                "Nội dung thân bài phân cảnh có Timestamps (Mốc thời gian)",
                "Đoạn kết (Outro) & CTA gợi ý video tiếp theo (End Screen)",
                "Mô tả video chuẩn SEO (SEO Description, Timestamps, Resource Links, 3-5 Hashtags)",
            ],
            suggested_length_guide="Long-form Video: 3 - 10 phút (Kịch bản 500-1500 từ) | Shorts: 30 - 60s (Kịch bản 80-140 từ).",
            key_elements=["SEO Title", "Thumbnail Concept", "5s Retention Hook", "Timeline Script", "SEO Description with Timestamps"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Hook kết quả trước/sau", "Câu hỏi gây tò mò tột độ", "Nêu sai lầm nghiêm trọng", "Trực quan hóa vấn đề"],
            time_or_line_constraint="5 đến 10 giây đầu tiên của video.",
            examples=[
                "Nếu bạn vẫn đang viết content theo cách này năm 2026, bạn đang lãng phí 80% ngân sách...",
                "Trong video này, mình sẽ hướng dẫn bạn từng bước tự động hóa toàn bộ quy trình quảng cáo.",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Đăng ký kênh (Subscribe)", "Bấm chuông thông báo", "Bình luận ý kiến", "Bấm vào link dưới phần mô tả"],
            tone_requirement="Tự nhiên, gắn liền với giá trị vừa chia sẻ trong video.",
            examples=[
                "Nếu video này hữu ích, hãy bấm Đăng ký kênh và nút Chuông để không bỏ lỡ bài học tiếp theo.",
                "Tải toàn bộ tài liệu miễn phí tại đường link mình để ở đầu phần Mô tả nhé.",
            ],
        ),
        constraints=[
            "Tiêu đề YouTube nên dưới 70 ký tự để hiển thị trọn vẹn trên điện thoại.",
            "Thumbnail text không để quá 4-5 từ.",
            "Không clickbait lừa dối người xem (nếu tiêu đề hứa hẹn gì thì video phải giải quyết điều đó).",
        ],
        best_practices=[
            "Tạo vòng lặp giữ chân (Retention loop) - liên tục mở ra các câu hỏi mở trước mỗi phân đoạn mới.",
            "Chuẩn bị sẵn phần mô tả SEO có phân chia chương (Chapters/Timestamps).",
        ],
        policy_guidelines=[
            "Tuân thủ nguyên tắc cộng đồng YouTube về an toàn nội dung và bản quyền âm thanh/hình ảnh.",
        ],
    ),
    PlatformId.SHOPEE: PlatformSpecification(
        platform_id=PlatformId.SHOPEE,
        display_name="Shopee E-commerce Listing",
        primary_objective="Tối ưu SEO tìm kiếm trên sàn TMĐT, vượt qua so sánh giá/chất lượng, tăng tỷ lệ nhấp và tỷ lệ chốt đơn (Add to Cart / Buy Now).",
        audience_behavior="Người dùng có nhu cầu mua sắm tức thì, so sánh nhiều gian hàng cùng lúc, đọc lướt bảng thông số, tìm kiếm voucher/quà tặng và bảo hành.",
        recommended_tones=["Thuyết phục", "Rõ ràng", "Minh bạch", "Nổi bật ưu đãi", "Đáng tin cậy"],
        structure=ContentStructure(
            primary_sections=[
                "Tiêu đề chuẩn SEO Shopee: [Thương hiệu] + [Tên sản phẩm] + [Đặc điểm nổi bật/Model] + [Công dụng/Phân loại]",
                "Đoạn mở đầu ngắn gọn: Định vị sản phẩm & Ưu đãi nóng",
                "Đặc điểm nổi bật & Lợi ích (Dạng gạch đầu dòng rõ ràng)",
                "Bảng thông số kỹ thuật chi tiết",
                "Hướng dẫn sử dụng & Bảo quản",
                "Chính sách bảo hành & Đổi trả & Cam kết chính hãng",
                "Call to action giục đặt mua",
                "Từ khóa Hashtag sàn TMĐT",
            ],
            suggested_length_guide="Mô tả hoàn chỉnh: 250 - 500 từ. Trình bày rõ ràng dạng gạch đầu dòng và phân mục hoa thị.",
            key_elements=["SEO Title Formula", "USP Bullet Points", "Tech Specs Table", "Warranty & Trust Box", "Hashtag Set"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Tiêu đề chuẩn SEO chứa từ khóa hot", "USP độc quyền", "Quà tặng kèm"],
            time_or_line_constraint="50 ký tự đầu tiên của tiêu đề sản phẩm và 2 dòng đầu của mô tả.",
            examples=[
                "[Chính Hãng] Tai Nghe Bluetooth AdGen SoundMax Chống Ồn Chủ Động ANC, Pin 40H - Bảo Hành 12 Tháng",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Thêm vào giỏ hàng", "Thu thập voucher sàn", "Mua ngay kẻo lỡ ưu đãi", "Chat với Shop để được tư vấn"],
            tone_requirement="Thúc giục nhẹ nhàng với ưu đãi cụ thể, củng cố niềm tin.",
            examples=[
                "Bấm 'MUA NGAY' và nhớ áp mã FREESHIP EXTRA & Voucher giảm giá của shop nhé!",
                "Inbox ngay cho Shop nếu bạn cần tư vấn chọn màu hoặc kích cỡ phù hợp.",
            ],
        ),
        constraints=[
            "Tiêu đề không nhồi nhét từ khóa spam vô nghĩa.",
            "Không để thông tin số điện thoại cá nhân hoặc link ngoài kéo khách khỏi sàn Shopee.",
            "Chỉ liệt kê khuyến mãi, giá, quà tặng khi người dùng cung cấp.",
        ],
        best_practices=[
            "Trình bày cấu trúc cực kỳ rõ ràng, phân cách giữa các phần bằng các ký hiệu phân đoạn dễ nhìn (✨, 📌, 💎).",
            "Nêu bật chính sách 1 đổi 1 hoặc bảo hành chính hãng để triệt tiêu nỗi sợ rủi ro của người mua hàng online.",
        ],
        policy_guidelines=[
            "Tuân thủ quy định đăng bán sản phẩm của Shopee: Không sử dụng từ ngữ cấm như 'trị dứt điểm 100%' cho mỹ phẩm/thực phẩm chức năng.",
        ],
    ),
    PlatformId.EMAIL: PlatformSpecification(
        platform_id=PlatformId.EMAIL,
        display_name="Email Marketing & Newsletter",
        primary_objective="Tối ưu tỷ lệ mở (Open Rate) qua Subject Line, duy trì tỷ lệ đọc (Click-through Rate) và thúc đẩy 1 hành động duy nhất.",
        audience_behavior="Đọc trong hộp thư cá nhân, thời gian chú ý ngắn, cảm giác dễ chịu với email viết như từ một người thật gửi riêng cho họ.",
        recommended_tones=["Trực tiếp", "Chân thành", "Cá nhân hóa", "Chuyên nghiệp", "Gợi mở"],
        structure=ContentStructure(
            primary_sections=[
                "Tiêu đề email (Subject Line - 3 phương án: Tò mò, Nỗi đau, Lợi ích trực tiếp <= 50 ký tự)",
                "Pre-header / Preview text (<= 40 ký tự hỗ trợ dòng tiêu đề)",
                "Lời chào cá nhân hóa (Personalized greeting: Chào [Tên],...)",
                "Đoạn mở đầu kết nối câu chuyện / vấn đề cá nhân",
                "Giá trị trọng tâm hoặc ưu đãi độc quyền",
                "Một nút bấm / Lời kêu gọi hành động duy nhất (Primary CTA)",
                "Tái bút (P.S.) nhấn mạnh điểm mấu chốt hoặc thời hạn",
            ],
            suggested_length_guide="Email ngắn: 100-180 từ | Newsletter/Story email: 200-350 từ.",
            key_elements=["3 Subject Lines", "Preview Text", "Personalized Body", "Single Focus CTA", "P.S. Section"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Subject line tò mò", "Cá nhân hóa nỗi đau", "Thông báo tin độc quyền"],
            time_or_line_constraint="Tiêu đề dưới 50 ký tự để không bị ẩn trên ứng dụng Mail điện thoại.",
            examples=[
                "[Tên] ơi, bạn đã thử cách viết bài này chưa?",
                "Bí quyết tối ưu chi phí quảng cáo (chỉ dành cho bạn)",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Bấm vào nút đăng ký", "Xem chi tiết ưu đãi", "Phản hồi email (Reply)", "Đặt lịch hẹn"],
            tone_requirement="Đơn giản, trực quan, tập trung vào 1 mục tiêu duy nhất.",
            examples=[
                "👉 Nhấp vào đây để nhận ưu đãi của bạn",
                "Bấm vào liên kết này để kích hoạt tài khoản ngay hôm nay",
            ],
        ),
        constraints=[
            "Mỗi email chỉ nên có 1 MỤC TIÊU DUY NHẤT (Single Focused Goal), không chèn 4-5 link khác nhau làm loãng hành động.",
            "Tránh các từ khóa kích hoạt bộ lọc spam (như 'FREE 100% KIẾM TIỀN NHANH').",
        ],
        best_practices=[
            "Luôn có dòng P.S. (Tái bút) ở cuối vì đây là phần được người đọc quét mắt nhiều nhất.",
            "Cung cấp 3-5 phương án Subject Line để A/B test tỷ lệ mở.",
        ],
        policy_guidelines=[
            "Tuân thủ luật chống spam (CAN-SPAM / GDPR): Luôn giữ tinh thần minh bạch và có lý do chính đáng để gửi thư.",
        ],
    ),
    PlatformId.LANDING_PAGE: PlatformSpecification(
        platform_id=PlatformId.LANDING_PAGE,
        display_name="Landing Page & Sales Page",
        primary_objective="Dẫn dắt người đọc qua hành trình thuyết phục hoàn chỉnh từ nhận thức đến quyết định mua hàng hoặc đăng ký form.",
        audience_behavior="Truy cập từ quảng cáo hoặc tìm kiếm, đánh giá trang trong 5 giây đầu, cuộn trang theo từng khối giá trị (sections) để tìm bằng chứng và lời giải đáp.",
        recommended_tones=["Thuyết phục", "Chuyên nghiệp", "Truyền cảm hứng", "Đáng tin cậy", "Rõ ràng"],
        structure=ContentStructure(
            primary_sections=[
                "Hero Section (H1 Value Proposition, H2 Sub-headline, Hero CTA, Social Proof badge)",
                "Problem & Pain Point Agitation (Mô tả thực trạng và nỗi đau khách hàng)",
                "Solution & Product Introduction (Sản phẩm là câu trả lời toàn diện)",
                "Features to Benefits Transformation (Tính năng chuyển thành lợi ích thực tế)",
                "Social Proof & Testimonials (Lời chứng thực, con số thực tế nếu có)",
                "Pricing & Offer Package (Bảng giá và quà tặng đi kèm)",
                "FAQ Section (Giải đáp 3-5 thắc mắc và từ chối thường gặp)",
                "Final Call To Action & Risk Reversal (Bảo đảm/Cam kết hài lòng)",
            ],
            suggested_length_guide="Full Landing Page Copy: 400 - 900 từ phân chia theo từng Section rõ ràng kèm wireframe layout gợi ý.",
            key_elements=["Hero Banner Copy", "Problem-Solution Matrix", "Benefit Cards", "FAQ Accordion", "Sticky/Final CTA"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["H1 Định vị giá trị độc nhất (Unique Value Proposition)", "H2 Giải quyết vấn đề cốt lõi"],
            time_or_line_constraint="Hero Section trong màn hình đầu tiên (Above the Fold).",
            examples=[
                "H1: Tự Động Hóa 80% Quy Trình Sáng Tạo Nội Dung Quảng Cáo Của Doanh Nghiệp Bạn",
                "H2: Nền tảng AI chuyên sâu giúp bạn tạo bài viết đa kênh chuẩn phong cách thương hiệu trong tích tắc.",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Đăng ký tài khoản dùng thử", "Đặt mua ngay", "Đặt lịch tư vấn 1-1", "Nhận bản demo"],
            tone_requirement="Mạnh mẽ, rõ ràng, nêu bật không có rủi ro.",
            examples=[
                "BẮT ĐẦU DÙNG THỬ MIỄN PHÍ - KHÔNG CẦN THẺ TÍN DỤNG",
                "NHẬN TƯ VẤN VÀ BÁO GIÁ NGAY HÔM NAY",
            ],
        ),
        constraints=[
            "Phải phân chia cấu trúc rõ ràng theo từng Khối (Section) để đội ngũ thiết kế/developer dễ dàng triển khai.",
            "Không sử dụng lời hứa suông mà không có luận điểm hoặc tính năng hỗ trợ.",
        ],
        best_practices=[
            "Chuyển đổi từng tính năng thành một card lợi ích 3 phần: [Tiêu đề lợi ích] + [Mô tả chi tiết] + [Icon minh họa gợi ý].",
            "Xây dựng phần FAQ tập trung xử lý các rào cản tâm lý mua hàng (Objection Handling).",
        ],
        policy_guidelines=[
            "Thông tin minh bạch về điều khoản sử dụng và chính sách hoàn tiền/bảo mật.",
        ],
    ),
    PlatformId.SEO: PlatformSpecification(
        platform_id=PlatformId.SEO,
        display_name="SEO Article & Blog Content",
        primary_objective="Thỏa mãn ý định tìm kiếm của người dùng (Search Intent), đạt thứ hạng cao trên Google SERP, giữ chân đọc lâu và chuyển đổi thành lead.",
        audience_behavior="Chủ động tìm kiếm câu trả lời cho thắc mắc, quét mục lục (Table of Contents), đọc lướt qua các tiêu đề H2/H3 để tìm đoạn thông tin cần thiết.",
        recommended_tones=["Chuyên gia", "Tường minh", "Đáng tin cậy", "Khách quan", "Hướng dẫn chi tiết"],
        structure=ContentStructure(
            primary_sections=[
                "Tiêu đề bài viết SEO (SEO Title Tag <= 60 ký tự, chứa từ khóa chính ở đầu)",
                "Thẻ Meta Description (140 - 160 ký tự, tóm tắt hấp dẫn có CTA click)",
                "Đoạn mở bài (Introduction: Xuất hiện từ khóa chính trong 100 từ đầu tiên, nêu lợi ích bài viết)",
                "Dàn ý mục lục chuẩn phân cấp Semantic (H2, H3, H4)",
                "Nội dung từng phần chuyên sâu, kèm ví dụ thực tế và checklist",
                "Phần FAQ chứa 3-4 câu hỏi thường gặp (chuẩn SEO FAQ Schema)",
                "Đoạn kết luận & Call to action nội bộ / tải tài liệu",
            ],
            suggested_length_guide="Bài viết chuẩn SEO: 800 - 1800 từ (Tùy độ sâu chủ đề). Dàn ý chi tiết + nội dung mẫu từng mục.",
            key_elements=["SEO Title & Meta", "Keyword Strategy", "H2/H3 Hierarchy", "Internal Link Hints", "FAQ Schema"],
        ),
        hook_guideline=HookGuideline(
            recommended_types=["Nêu vấn đề và giải pháp toàn diện", "Dữ liệu/Thực trạng ngành", "Mục tiêu rõ ràng"],
            time_or_line_constraint="Đoạn mở bài 2-3 câu đầu tiên chứa từ khóa chính.",
            examples=[
                "Bạn đang tìm kiếm phương pháp tối ưu hóa chi phí quảng cáo nhưng chưa biết bắt đầu từ đâu? Hướng dẫn toàn diện dưới đây sẽ giúp bạn...",
            ],
        ),
        cta_guideline=CtaGuideline(
            primary_actions=["Đọc thêm bài viết liên quan", "Tải checklist/tài liệu", "Đăng ký nhận bản tin", "Dùng thử sản phẩm giải pháp"],
            tone_requirement="Tự nhiên, mang tính tư vấn và cung cấp thêm giá trị hữu ích.",
            examples=[
                "Tải ngay bản mẫu kế hoạch marketing 2026 tại đây để áp dụng cho doanh nghiệp của bạn.",
                "Trải nghiệm công cụ tự động hóa AdGen AI miễn phí để tối ưu bài viết của bạn.",
            ],
        ),
        constraints=[
            "BẮT BUỘC: Title tag nên dưới 60 ký tự để không bị cắt trên Google kết quả tìm kiếm.",
            "BẮT BUỘC: Meta description trong khoảng 140-160 ký tự.",
            "Không nhồi nhét từ khóa gượng ép (mật độ từ khóa tự nhiên khoảng 1-2.5%).",
            "Cấu trúc heading phải đúng thứ tự H1 -> H2 -> H3, không nhảy cóc cấp bậc.",
        ],
        best_practices=[
            "Áp dụng nguyên tắc Google E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness).",
            "Sử dụng bảng biểu, danh sách có thứ tự và hộp ghi chú (Takeaways) để tăng thời gian đọc trang (Dwell Time).",
        ],
        policy_guidelines=[
            "Nội dung hữu ích thực sự cho con người (Helpful Content), không tạo nội dung rác hàng loạt.",
        ],
    ),
}
