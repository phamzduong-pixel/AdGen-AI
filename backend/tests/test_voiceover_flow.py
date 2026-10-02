import sys
import os
import json
import asyncio

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('backend'))

from httpx import AsyncClient, ASGITransport
from app.main import app

async def run_tests():
    print("=== RUNNING ADGEN VOICE STUDIO COMPREHENSIVE FLOW TESTS ===\n")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # TEST 1: Valid Request with integer message_id and float pitch
        print("--- TEST 1: Valid Request (message_id=22, pitch=0.0) ---")
        payload_valid = {
            "text": "Chào mừng bạn đến với AdGen AI! Kịch bản đã sẵn sàng.",
            "voice_id": "vi-VN-HoaiMyNeural",
            "speed": 1.0,
            "pitch": 0,
            "message_id": 22
        }
        res1 = await client.post("/voiceover/generate", json=payload_valid)
        print(f"Status Code: {res1.status_code}")
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
        data1 = res1.json()
        print(f"Success: {data1['success']}")
        print(f"Audio ID: {data1['audio_id']}")
        print(f"Audio URL: {data1['audio_url']}")
        print(f"Download URL: {data1['download_url']}")
        print(f"Duration: {data1['duration_seconds']}s")
        print(f"File Size: {data1['file_size_bytes']} bytes")
        print("-> TEST 1 PASSED: Valid MP3 generated successfully!\n")

        # TEST 2: Audio Stream & Download Verification
        print("--- TEST 2: Audio File Streaming & Download Headers ---")
        audio_url = data1['audio_url']
        res_stream = await client.get(audio_url)
        print(f"Stream Status: {res_stream.status_code}")
        print(f"Content-Type: {res_stream.headers.get('content-type')}")
        print(f"Content-Disposition (inline): {res_stream.headers.get('content-disposition')}")
        assert res_stream.status_code == 200
        assert "audio/mpeg" in res_stream.headers.get("content-type", "")
        assert "inline" in res_stream.headers.get("content-disposition", "")

        download_url = data1['download_url']
        res_download = await client.get(download_url)
        print(f"Download Status: {res_download.status_code}")
        print(f"Content-Disposition (attachment): {res_download.headers.get('content-disposition')}")
        assert res_download.status_code == 200
        assert "attachment" in res_download.headers.get("content-disposition", "")
        print("-> TEST 2 PASSED: Audio stream & download endpoints operational!\n")

        # TEST 3: Backend Validation 422 (Empty Text)
        print("--- TEST 3: Invalid Request (Empty Text) -> 422 Unprocessable Entity ---")
        payload_invalid_text = {
            "text": "",
            "voice_id": "vi-VN-HoaiMyNeural",
            "message_id": 22
        }
        res3 = await client.post("/voiceover/generate", json=payload_invalid_text)
        print(f"Status Code: {res3.status_code}")
        print(f"Raw 422 response body: {res3.json()}")
        assert res3.status_code == 422
        errors = res3.json().get("detail", [])
        assert len(errors) > 0
        assert any(e.get("loc") == ["body", "text"] for e in errors)
        print("-> TEST 3 PASSED: 422 validation returned as expected.\n")

        # TEST 4: Backend Validation 422 (Speed out of bounds > 2.0)
        print("--- TEST 4: Invalid Request (Speed = 5.0 > 2.0) -> 422 Unprocessable Entity ---")
        payload_invalid_speed = {
            "text": "Lời thoại kiểm tra tốc độ",
            "speed": 5.0
        }
        res4 = await client.post("/voiceover/generate", json=payload_invalid_speed)
        print(f"Status Code: {res4.status_code}")
        print(f"Raw 422 response body: {res4.json()}")
        assert res4.status_code == 422
        errors4 = res4.json().get("detail", [])
        assert any("speed" in str(e.get("loc", [])) for e in errors4)
        print("-> TEST 4 PASSED: 422 validation caught invalid speed.\n")

    print("=== ALL BACKEND INTEGRATION TESTS PASSED ===")

asyncio.run(run_tests())
