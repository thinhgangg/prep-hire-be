# 🎙️ Hướng dẫn chạy Whisper STT bằng GPU Google Colab

> **Mục đích:** Thay thế backend STT chạy local bằng GPU miễn phí của Google Colab — nhanh hơn, không cần cài đặt gì trên máy.  
> **File notebook:** [`docs/COLAB_STT_GPU.ipynb`](../docs/COLAB_STT_GPU.ipynb)

---

## 🗺️ Kiến trúc khi dùng Colab

```
Frontend (localhost:5173)
        │
        │  POST /api/v1/stt/jobs   (upload audio)
        │  GET  /api/v1/stt/jobs/{id}  (poll kết quả)
        ▼
  STT Backend ← bình thường: localhost:8000
              ← khi dùng Colab: https://xxxx.ngrok-free.app
        │
        │  Whisper turbo model
        ▼
     GPU T4 (Google Colab)
```

> ℹ️ Chỉ STT backend thay đổi. **AI backend** (`port 9001`) và frontend vẫn chạy bình thường trên máy.

---

## 📋 Chuẩn bị (làm 1 lần)

### 1. Lấy ngrok Authtoken miễn phí

1. Truy cập [https://ngrok.com](https://ngrok.com) → **Sign up** (miễn phí)
2. Vào **Dashboard → Your Authtoken**
3. Copy token (dạng: `2abc...XYZ_...`)

> Giữ token này, sẽ cần dán vào Colab ở bước sau.

---

## 🚀 Các bước chạy

### Bước 1 — Mở notebook trên Google Colab

Chọn một trong hai cách:

**Cách A:** Upload file lên Colab
1. Vào [colab.research.google.com](https://colab.research.google.com)
2. **File → Upload notebook**
3. Chọn file `prep-hire-be/docs/COLAB_STT_GPU.ipynb`

**Cách B:** Mở từ GitHub (nếu repo public)
1. Vào Colab → **File → Open notebook → GitHub**
2. Dán URL: `https://github.com/thinhgangg/prep-hire-be`
3. Chọn nhánh `An` → chọn `docs/COLAB_STT_GPU.ipynb`

---

### Bước 2 — Đổi Runtime sang GPU T4

> ⚠️ **Bắt buộc.** Không có GPU thì Whisper sẽ rất chậm.

1. Click **Runtime** (trên thanh menu)
2. Chọn **Change runtime type**
3. Mục **Hardware accelerator** → chọn **T4 GPU**
4. Nhấn **Save**

![GPU selection](https://i.imgur.com/placeholder.png)

---

### Bước 3 — Chạy Cell 1: Cài thư viện

Click ▶️ ở **Cell 1** (hoặc `Shift+Enter`).

```python
%pip -q install faster-whisper 'av<19' fastapi uvicorn python-multipart pyngrok ...
```

Chờ đến khi thấy dòng `Successfully installed...` — thường mất **1-2 phút**.

> ℹ️ `av<19` được ghim cứng vì PyAV 19 không tương thích với faster-whisper hiện tại.

---

### Bước 4 — Chạy Cell 2: Tạo server code

Click ▶️ ở **Cell 2**.

```
Server file created
```

Nếu thấy dòng trên là thành công. Cell này chỉ tạo file Python chứa FastAPI server — chưa chạy.

---

### Bước 5 — Chạy Cell 3: Khởi động server + ngrok

Click ▶️ ở **Cell 3** (cell cuối cùng).

**Luồng thực hiện tự động:**
1. Khởi động uvicorn server trên GPU
2. Load model Whisper `turbo` lên VRAM *(lần đầu mất ~3-5 phút)*
3. Chờ server sẵn sàng (tự động health check)
4. Hỏi ngrok authtoken → **dán token của bạn vào ô nhập ẩn, nhấn Enter**
5. Tạo ngrok tunnel
6. In ra URL công khai

**Output mẫu khi thành công:**
```
Đang tải model turbo lên GPU; lần đầu có thể mất vài phút...
Whisper GPU đã sẵn sàng. Đang tạo ngrok tunnel...
Dán ngrok authtoken (ký tự sẽ được ẩn): [nhập token ở đây]
VITE_API_BASE_URL=https://abcd-1234.ngrok-free.app
Health=https://abcd-1234.ngrok-free.app/health
GIỮ CELL NÀY TIẾP TỤC CHẠY. Không bấm Stop.
```

> ⚠️ **KHÔNG bấm Stop ô cell này.** Server sẽ dừng nếu bạn ngắt cell.

---

### Bước 6 — Kiểm tra server hoạt động

Mở trình duyệt, truy cập URL `/health` vừa in ra:

```
https://abcd-1234.ngrok-free.app/health
```

✅ Phản hồi đúng:
```json
{
  "status": "ok",
  "model": "turbo",
  "device": "cuda",
  "compute_type": "float16"
}
```

> ⚠️ Chỉ tiến hành bước tiếp theo khi thấy `"device": "cuda"`. Nếu thấy `"device": "cpu"` thì runtime chưa có GPU.

---

### Bước 7 — Cập nhật `.env` của Frontend

Mở file `prep-hire-fe/.env`, **thay đổi** biến `VITE_BE_URL`:

```env
# ← Trước (local)
VITE_BE_URL=http://localhost:8000

# ← Sau (Colab)
VITE_BE_URL=https://abcd-1234.ngrok-free.app
```

> ℹ️ `VITE_AI_URL` (port 9001) **không đổi** — AI backend vẫn chạy local.

---

### Bước 8 — Khởi động lại Frontend

```powershell
# Dừng frontend hiện tại (Ctrl+C), sau đó:
cd D:\...\prep-hire-fe
npm run dev
```

Frontend sẽ tự động gửi audio đến Colab GPU thay vì localhost.

---

## 🔄 Khi Colab bị disconnect / timeout

Colab miễn phí giới hạn ~12 giờ/session. Khi session hết:

1. **URL ngrok sẽ thay đổi** → cần lấy URL mới
2. Chạy lại từ **Bước 5** (không cần chạy lại Cell 1 và 2)
3. Cập nhật `VITE_BE_URL` trong `.env` với URL mới
4. Restart frontend

---

## ↩️ Quay lại dùng STT local

Khi muốn dùng `prep-hire-be` chạy local thay vì Colab:

```env
# prep-hire-fe/.env
VITE_BE_URL=http://localhost:8000
```

Sau đó restart frontend (`npm run dev`).

---

## ❗ Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| `Runtime error: Whisper API không sẵn sàng` | Server khởi động chậm hoặc lỗi GPU | Xem log tại `/content/stt_api.log` trong Colab |
| `/health` trả về `"device": "cpu"` | Chưa chọn T4 GPU trong runtime | Runtime → Change runtime type → T4 GPU |
| `ngrok đã tạo URL nhưng không truy cập được` | ngrok token sai hoặc đã dùng hết quota | Kiểm tra token trên dashboard ngrok |
| Frontend vẫn gọi `localhost:8000` | Chưa restart sau khi sửa `.env` | Ctrl+C → `npm run dev` lại |
| `Failed to fetch` trên trang processing | URL Colab đã đổi sau khi reconnect | Lấy URL mới từ output Colab và cập nhật `.env` |
| Cell 1 bị lỗi `av` | PyAV version conflict | Đảm bảo lệnh install có `'av<19'` |

---

## 📝 Ghi chú kỹ thuật

- Model sử dụng: **Whisper `turbo`** — cân bằng giữa tốc độ và độ chính xác
- Ngôn ngữ: **Tiếng Việt** (`language="vi"`)
- Compute type: **float16** (tận dụng tối đa VRAM T4)
- VAD filter: bật — loại bỏ khoảng lặng tự động
- Mỗi job STT chạy **tuần tự** (1 worker) để tránh OOM trên T4 4GB VRAM
