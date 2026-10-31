# Tích hợp KorvaTTS trong backend

KorvaTTS chạy trực tiếp trong `prep-hire-be`; không có server TTS hoặc port riêng.
Model chỉ được nạp khi frontend gọi `POST /api/v1/tts/speech` lần đầu.

## Kiến trúc

```text
Frontend :5173
  |  POST /api/v1/tts/speech { text }
  v
Backend :8000
  |-- app/api/tts.py              HTTP API
  |-- app/services/tts_service.py lazy-load KorvaTTS + cache WAV
  `-- data/
      |-- huggingface/            model weights (không commit Git)
      `-- tts_cache/              WAV đã sinh (không commit Git)
```

AI backend vẫn chỉ tạo nội dung câu hỏi. Khi FE nhận câu hỏi mới, FE gọi BE để
tạo WAV và tự phát. Nếu TTS lỗi, câu hỏi chữ và luồng phỏng vấn vẫn hoạt động.

### Prewarm ngay khi AI chọn xong câu hỏi

Ngay sau khi AI chọn được câu hỏi (trước lúc commit session và trả response về
FE), AI gửi một thông báo bất đồng bộ tới:

```text
POST http://localhost:8000/api/v1/tts/prewarm
```

BE trả `202` ngay rồi tạo audio trong background. Vì vậy thời gian commit DB,
serialize response, truyền response và render FE được chạy song song với TTS.
Khi FE gọi `/speech`, service dùng file đã cache hoặc chờ đúng inference đang
chạy; không sinh trùng hai lần. Nếu BE/TTS không sẵn sàng, AI vẫn trả câu hỏi
bình thường.

Cấu hình trong `prep-hire-ai/.env`:

```env
TTS_PREWARM_ENABLED=true
TTS_PREWARM_URL=http://localhost:8000/api/v1/tts/prewarm
TTS_PREWARM_NOTIFY_TIMEOUT_SECONDS=3
```

## Cài đặt

Yêu cầu Python 3.10 trở lên. Tại thư mục backend:

```powershell
cd D:\D\PBL6\prep-hire-be
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

KorvaTTS tải weights từ Hugging Face trong request đầu tiên và lưu tại
`data/huggingface`. Có thể tải trước để request đầu không phải chờ:

```powershell
$env:HF_HOME="$PWD\data\huggingface"
$env:HF_HUB_DISABLE_XET="1"
python -c "from huggingface_hub import snapshot_download; snapshot_download('dogenthq/KorvaTTS', allow_patterns=['onnx/*','voice_styles/*'], max_workers=1)"
```

`max_workers=1` được khuyến nghị trên Windows để tránh kết nối Hugging Face bị
reset khi tải nhiều file ONNX song song.

## Cấu hình `.env`

```env
TTS_MAX_TEXT_LENGTH=1500
KORVA_VOICE=hoang_nam
KORVA_TOTAL_STEPS=16
KORVA_SPEED=1.05
KORVA_CACHE_DIR=data/tts_cache
KORVA_HF_HOME=data/huggingface
```

- `KORVA_VOICE`: giọng cố định. Dự án đang dùng `hoang_nam`.
- `KORVA_TOTAL_STEPS`: `16` cân bằng tốc độ/chất lượng; `8` nhanh hơn, `32` đẹp hơn.
- `KORVA_SPEED`: tốc độ đọc, mặc định `1.05`.
- `KORVA_CACHE_DIR`: cache WAV theo nội dung câu hỏi và cấu hình giọng.

Sau khi đổi `.env`, cần restart BE.

## Chạy hệ thống

Không cần chạy TTS riêng. Chỉ chạy BE như bình thường:

```powershell
cd D:\D\PBL6\prep-hire-be
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Kiểm tra trạng thái:

```text
GET http://localhost:8000/api/v1/tts/health
```

Trước request đầu tiên, `loaded` là `false`. Sau lần tạo âm thanh đầu tiên,
`loaded` là `true`.

Tạo âm thanh:

```http
POST http://localhost:8000/api/v1/tts/speech
Content-Type: application/json

{
  "text": "Bạn hãy giới thiệu ngắn gọn về kinh nghiệm phù hợp nhất với vị trí này."
}
```

Response là `audio/wav`. Header `X-TTS-Cache` có giá trị `miss` ở lần đầu và
`hit` khi câu hỏi đã có trong cache.

## Hành vi frontend

`prep-hire-fe/src/services/ttsApi.ts` gọi endpoint BE và phát WAV khi câu hỏi
thay đổi. Phòng phỏng vấn có nút **Đọc lại câu hỏi** và **Dừng đọc**. Trình
duyệt có thể chặn autoplay; trong trường hợp đó người dùng chỉ cần bấm **Đọc
lại câu hỏi**.

## Xử lý sự cố

### Request đầu chậm

Model đang được tải hoặc khởi tạo ONNX. Các request sau tái sử dụng model trong
RAM; câu đã đọc còn được lấy trực tiếp từ cache WAV.

### Hugging Face bị ngắt kết nối

Chạy lại lệnh tải trước bên trên. File đã tải sẽ được tiếp tục, không tải lại
toàn bộ.

### Muốn giảm CPU

Đặt `KORVA_TOTAL_STEPS=8` rồi restart BE. Khóa cache đã bao gồm số steps nên
không cần xóa cache cũ.

### TTS lỗi nhưng interview vẫn phải chạy

FE bắt lỗi TTS độc lập và vẫn hiển thị câu hỏi. Endpoint AI/STT không phụ thuộc
vào việc KorvaTTS có nạp thành công hay không.
