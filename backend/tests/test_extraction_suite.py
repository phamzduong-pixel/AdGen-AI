import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.voiceover.extractor import VoiceoverScriptExtractor

cases = [
    {
        "name": "Test Case 1: TikTok Multi-Scene Script",
        "text": '''
### Cảnh 1 — 0-3 giây (Hook)
* Hình ảnh: Cận cảnh hộp chân gà sốt Thái cay xé lưỡi, khói cay và ớt tươi bốc lên
* Text trên màn hình: CẢNH BÁO: CỰC CAY!
* Hiệu ứng âm thanh: Tiếng cắn giòn sần sật 'Rốp rốp'
* Voiceover: "Trời ơi, nếu bạn là tín đồ ăn cay thì dừng lại ngay 3 giây!" (giọng hào hứng, giật mình)

### Cảnh 2 — 3-10 giây (Problem & Pain point)
* Visual: Bạn trẻ ngồi xem phim nửa đêm, bụng cồn cào thèm ăn vặt
* Lời thoại: "Nửa đêm cày phim mà miệng buồn ghê gớm, tìm đồ ăn ngon thì toàn quán đóng cửa?" (thì thầm đồng cảm)
* SFX: Tiếng đồng hồ tích tắc

### Cảnh 3 — 10-18 giây (Solution & Experience)
* Hình ảnh: Người review dùng đũa gắp miếng chân gà rút xương sốt đẫm gia vị đưa vào miệng
* Text: CHÂN GÀ RÚT XƯƠNG CAY BÙNG NỔ
* Voiceover: "Thử ngay chân gà rút xương sốt cay Tứ Xuyên nhà Bon Bon. Chân gà giòn sần sật, sốt chua ngọt cay tê tái, ăn là dính liền!"
* Hiệu ứng: tiếng ting lấp lánh

### Cảnh 4 — 18-25 giây (Call to Action)
* Visual: Tay bấm vào giỏ hàng góc trái màn hình, flash sale giảm giá 30%
* Lời thoại: "Bấm ngay vào giỏ hàng bên dưới để săn deal mua 2 tặng 1 chỉ trong hôm nay thôi nhé!"
'''
    },
    {
        "name": "Test Case 2: YouTube Script with Timestamps",
        "text": '''
[00:00 - 00:05] Intro
- Camera: Toàn cảnh bàn làm việc hiện đại, ánh sáng ấm
- Visual cue: Host cầm cuốn sổ tay thông minh
- Narration: "Chào mừng các bạn đã quay trở lại với kênh của mình! Hôm nay mình sẽ bật mí một bí quyết giúp tăng 200% năng suất làm việc mỗi ngày." (cười nhẹ)

[00:05 - 00:20] Nội dung chính
- Visual: Zoom cận cảnh ứng dụng quản lý công việc trên tablet
- SFX: Tiếng lật trang sách nhẹ nhàng
- Lời thoại: "Bạn có bao giờ cảm thấy dù đã làm việc cả ngày nhưng danh sách việc cần làm vẫn dài dằng dặc? Đó là vì bạn chưa biết đến phương pháp Time Blocking này thôi."
- Ghi chú đạo diễn: Host nói với tốc độ vừa phải, tự tin.

[00:20 - 00:30] Kêu gọi hành động
- On-screen text: SUBSCRIBE ĐỂ KHÔNG BỎ LỠ
- Voiceover: "Đừng quên bấm like và đăng ký kênh để nhận thêm nhiều mẹo hữu ích mỗi tuần nhé!"
'''
    },
    {
        "name": "Test Case 3: Marketing Strategy & Persona (Non-dialogue)",
        "text": '''
# KẾ HOẠCH CHIẾN DỊCH QUẢNG CÁO TẾT 2025

## 1. Phân tích đối tượng mục tiêu (Target Persona)
- Độ tuổi: 22 - 35 tuổi
- Giới tính: Nam và Nữ
- Thu nhập: 15 - 30 triệu/tháng
- Sở thích: Mua sắm quà biếu, công nghệ mới, quan tâm sức khỏe gia đình

## 2. Thông điệp cốt lõi (Key Message)
Món quà sức khỏe trọn vẹn yêu thương cho gia đình dịp năm mới.

## 3. Kênh truyền thông triển khai (Channels)
- Facebook Ads: Chạy bài viết carousel và video ngắn
- TikTok Ads: Hợp tác với 5 micro-influencer ngành ẩm thực
- Google Search: Nhắm các từ khóa 'quà tết ý nghĩa', 'hộp quà tết cao cấp'

## 4. Ngân sách & KPI
- Tổng ngân sách: 50.000.000 VNĐ
- Dự kiến đạt 500.000 lượt tiếp cận và 1.200 chuyển đổi.
'''
    }
]

print("=== STARTING EXTRACTION TEST SUITE ===\n")
for case in cases:
    res = VoiceoverScriptExtractor.extract(case["text"])
    print(f"=== {case['name']} ===")
    print(f"Status: {res.status}")
    print(f"Blocks extracted: {res.dialogue_blocks_count}")
    print(f"Warning message: {res.warning_message}")
    print("Cleaned Script Content:")
    print("--------------------------------------------------")
    print(res.cleaned_script)
    print("--------------------------------------------------\n")

print("=== STARTING TTS SYNTHESIS TEST ON EXTRACTED SCRIPT (TEST CASE 1) ===")
import asyncio
from app.services.voiceover.voiceover_service import VoiceoverService
from app.schemas.voiceover import VoiceoverGenerateRequest

async def run_tts():
    service = VoiceoverService()
    case1_extracted = VoiceoverScriptExtractor.extract(cases[0]["text"]).cleaned_script
    print(f"Feeding {len(case1_extracted)} chars of pure spoken dialogue to VoiceoverService...")
    
    req = VoiceoverGenerateRequest(
        text=case1_extracted,
        voice_id="vi-VN-HoaiMyNeural",
        speed=1.0,
        pitch=0.0
    )
    res = await service.generate_voiceover(req)
    print(f"Synthesized Successfully!")
    print(f"Audio ID: {res.audio_id}")
    print(f"Audio URL: {res.audio_url}")
    print(f"Download URL: {res.download_url}")
    print(f"File Size: {res.file_size_bytes:,} bytes")
    print(f"Duration: {res.duration_seconds} seconds")
    print(f"Voice Name: {res.voice_name}")
    print(f"Cleaned Text Fed to TTS:\n\"{res.cleaned_text}\"")

asyncio.run(run_tts())



